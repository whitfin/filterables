"""
Run from the repository root: uv run --with uvicorn uvicorn tests.example:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from filterables import Filterable
from filterables.deps import filters, paginate
from filterables.filters import Filters
from filterables.openapi import with_filter_docs
from filterables.pages import Pagination, Paginator


# create a simple Person representation in SQL
class Person(Filterable, SQLModel, table=True):
    id: str = Field(primary_key=True)
    age: int
    name: str


# create our engine in memory
engine = create_engine(
    "sqlite://",
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
)


# bind our models on startup and populate some people
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Person(id="1", age=18, name="Alice"),
                Person(id="2", age=25, name="Bob"),
                Person(id="3", age=30, name="Charlie"),
                Person(id="4", age=35, name="Dana"),
                Person(id="5", age=42, name="Eve"),
            ]
        )
        session.commit()
    yield
    engine.dispose()


# create our FastAPI application and bind the documentation types
app = FastAPI(title="Filterables Example", lifespan=lifespan)
app.openapi = with_filter_docs(app.openapi)


@app.get("/person")
def find_people(filters: Filters = Depends(filters), paginator: Paginator = Depends(paginate)) -> Pagination[Person]:
    """
    Filter and paginate `Person` rows inside the SQL database.
    """
    with Session(engine) as session:
        return paginator.exec(session, select(Person), filters)
