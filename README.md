# Filterables

Filtering and pagination for Pydantic and SQLModel, with FastAPI integration.

A `Filterable` is a simple Pydantic model which can be used with SQLModel to
get you up and running with filtering and pagination quickly. By providing
bindings for FastAPI, `filterables` makes it quick and easy to transform query
parameters into filters inside your SQLModel queries.

## Installation

To get started with `filterables`, install it from this repository:

```bash
pip install git+https://github.com/whitfin/filterables.git@0.8.0
```

If you're using a `pyproject.toml`, you can use this syntax as a dependency:

```toml
dependencies = [
    "filterables @ git+https://github.com/whitfin/filterables.git@0.8.0"
]
```

At some point this library might make it to PyPI, but until then you can
feel free to fork this repository for peace of mind as needed!

## Getting Started

Setting a class as `Filterable` is extremely simple:

```python
from filterables import Filterable

class MyClass(Filterable):
    id: str
```

The `Filterable` class is a subclass of a Pydantic `BaseModel`, so you can
use all the usual Pydantic flavour with this.

To use it alongside SQLModel, again just extend `SQLModel` exactly as you
would with Pydantic:

```python
from filterables import Filterable
from sqlmodel import SQLModel

class MyClass(Filterable, SQLModel):
    id: str
```

Rather than combining both into a single parent class, these two classes
are kept separate in order to support multiple workflows (described later).

## Filtering

Filtering is handled via the `Filters` class, which provides various common
operators for filtering data. Filters are created from a map of paths to an
operation, so for example:

```python
from filterables import Filterable
from filterables.filters import Filters
from sqlmodel import SQLModel

# demonstration filterable class
class Person(Filterable, SQLModel):
    id: str
    age: int
    name: str

# query ages 18-35
filters = Filters({
    "age": {
        "$gt": 18,
        "$lt": 35
    }
}}

# select all people
query = select(Person)

# apply the filters to the query
query = filters.bind(session, query)

# execute the query as usual
value = session.exec(query).all()
```

In this case we are using the path `age` and looking for values between 18
and 35. The current set of supported operators is as follows, as well as the
fields required to create them:

| Operator    | Fields   | Notes                                                  |
|-------------|----------|--------------------------------------------------------|
| Between     | $gt, $lt | Look for numeric values between upper and lower bounds |
| Equals      | $eq      | Look for a value based on equality                     |
| GreaterThan | $gt      | Look for numeric values above a lower bound            |
| Has         | $has     | Look for existence of a field (non-null)               |
| In          | $in      | Like $eq but with support for multiple values          |
| Like        | $like    | Look for a specific pattern in a value                 |
| LessThan    | $lt      | Look for numeric values below an upper bound           |
| NotEquals   | $ne      | Look for a value based on inequality                   |
| NotIn       | $nin     | Like $ne but with support for multiple values          |
| Unlike      | $unlike  | Like $like but with an inverted pattern                |

In almost all cases these operators are passed to SQL directly and will behave
in the same way your SQL engine would in case of e.g. mismatching types, etc.

## Pagination

A `Paginator` is included with `filterables` to enable pagination of resources with
a very simple interface.

If we look at how we'd add pagination to the filtered example above, we can see that
it's very straightforward:

```python
from filterables.pages import Paginator

# select all people
query = select(Person)

# apply the filters to the query
query = filters.bind(session, query)

# paginate people
pages = Paginator(
    limit=25,
    offset=0,
    sorting=["age:desc"]
)

# execute the query, but using a paginator
value = paginator.exec(session, query)

# OR: you can also combine with filters directly
value = paginator.exec(session, query, filters)
```

Rather than retrieving a full list of people, we'll now get a `Pagination` which
contains up to 25 people, sorted by oldest first. A pagination contains the total
count of matching rows, as well as the page of items based on your parameters.

```python
Pagination(
    count=100,
    results=[
        # ...
    ]
)
```

A pagination also holds reference to the filters and paginator used to create it,
for easier debugging and visibility down the chain.

## Nested Filterables

Filterables provides access to the `Nestable` column type for SQLModel, which
enables storing inner documents within a JSON column:

```python
from filterables import Filterable, Nestable

class MyInnerFilterable(Filterable):
    age: int
    name: str

class MyFilterable(Filterable, SQLModel):
    id: str
    data: MyInnerFilterable = Nestable(MyInnerFilterable)
```

Any (de)serialization is taken care of automatically, and you can still filter
just like any other column type (using a `.` to split the path):

```python
filters = Filters({
    "data.age": {
        "$gt": 18,
        "$lt": 35
    }
}}
```

You can access any level of nesting inside your JSON column, so you can chain
multiple segments (e.g. `data.data.data.age`) to your heart's content!

Filterables also includes a freeform JSON structure `Jsonable`, an empty Pydantic
model with extra properties allowed. If you wish to store arbitray JSON, you can
use this type alongside `Nestable` to still support all `Filterable` functionality.

## FastAPI Integration

Using `filterables` alongside FastAPI is very simple, and all types in this
project contain documentation for OpenAPI.

* Pagination is directly deserialized from query parameters
    * `?limit=X&offset=Y&sort=Z1:asc&sort=Z2:desc`
* Filters are deserialized from a URL encoded `filters` query parameter:
    * `?filters=%7B%22age%22%3A%7B%22%24gt%22%3A18%2C%22%24lt%22%3A35%7D%7D`

If we look at the earlier examples, let's add them within a FastAPI route to
create a JSON-based pagination via query parameters:

```python
from filterables.deps import filters, paginate
from filterables.filters import Filters
from filterables.pages import Paginator

# demonstration filterable class
class Person(Filterable, SQLModel):
    id: str
    age: int
    name: str


@app.get("/person")
def find_resources(filters: Filters = Depends(filters), paginator: Paginator = Depends(paginate)) -> Pagination[Person]:
    return paginator.exec(session, select(Person), filters)
```

This will select a filtered page based on query parameters and return the
pagination directly. The returned `Pagination` will automatically serialize
the JSON in the form:

```json5
{
    "count": 100,
    "params": {
        "limit": 25,
        "offset": 0,
        "sorting": [
            // sorters
        ],
        "excludes": [
            // exclusions
        ],
    },
    "filters": {
        // filters
    },
    "results": [
        // people
    ]
}
```

A paginator also supports the `?excludes=X` query parameter. This can be used to
strip fields out of the response from your SQL table; but be aware that this will
set the fields to `None` regardless of whether their type is designated as optional.

By default, all empty objects and values will be skipped from the response. You
can customize this behaviour using a custom Pydantic serializer on your model class.

## Custom Sorting

There are cases where you might wish to use different sorting, or even sort on a
virtual field. This can be done by creating a subclass of `Sorter`, which can then
modify a query dynamically.

A `Sorter` can attach things to the query directly, such as virtual columns. In the
simplest case, we could sort using a `<field>_<direction>` syntax as follows:

```python
import regex
from filterables import Filterable
from filterables.sorters import Sorter

class MySorter(Sorter):

    @classmethod
    def priority(cls) -> int:
        """
        Define our Sorter priority order.
        """
        return 1

    @classmethod
    def sort(cls, session, query, model, sorting: str) -> SelectOfScalar[Filterable] | None:
        """
        Apply our Sorter to the current query.
        """
        # use a pattern to split up our sorting parameter
        scoring = regex.match(r"^(\w+)_(asc|desc)$", sorting)

        # not this format
        if not scoring:
            return None

        # get the parameter values
        cap = scoring.allcaptures()
        path = cap[1]
        direct = capt[2]

        # access the model field
        field = getattr(model, path)

        # modify the query to filter on the column in the direction specified
        return query.order_by(field.desc() if direct == "desc" else field.asc())
```

Each sorter defines a priority to determine precedence, with lower being checked
sooner. All internal sorters will be in the 900 range, so anything lower than that
will result in your sorter being checked first. If your sorter cannot sort the current
parameter, it should return `None`.

## Compatibility

Please note that SQLModel is still fairly new, and does not have a commitment to a
specific API yet. As such this project will remain in the 0.x version line and has
limited typing support due to the wide use of `Any` in SQLModel.

The current version of this project supports SQLite, MySQL/MariaDB and PostgreSQL
drivers for SQLModel. Each is tested fully in the CI/CD pipeline in the GitHub
repository.

MSSQL is support for top-level fields, but nested JSON comparisons **will** cause
errors for mismatched types. Unless you can guarantee the types match, you should
avoid using nested fields with MSSQL. This dialect is still in CI/CD, but marked
as fallible due to these types of failures.

The easiest way to know if `filterables` will work for you is to try it out; please
feel free to file issues as needed!
