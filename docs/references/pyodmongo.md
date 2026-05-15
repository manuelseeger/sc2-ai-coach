# PyODMongo Documentation Mirror

Source: https://pyodmongo.dev/

Captured: 2026-05-04

This file is a cleaned, LLM-friendly mirror of the English documentation published on pyodmongo.dev and its English subpages from the sitemap.

Included pages:

- Overview
- Getting Started
- DbModel
- Save
- Find
- Delete
- Query Operators
- Use with FastAPI
- Indexes
- Aggregation
- Contributing
- Release Notes

Notes:

- Repeated site navigation, theme footer, language switchers, and badge clutter were removed.
- Content is normalized for reading and retrieval, not for pixel-perfect reproduction.

---

## Overview

Source: https://pyodmongo.dev/

PyODMongo is a Python Object-Document Mapper for MongoDB built on top of Pydantic v2. It aims to keep MongoDB documents aligned with Python object structure, including nested objects and referenced objects, while supporting automatic population.

### Key Features

- Integration with Pydantic for validation and modeling.
- Automatic schema generation from Pydantic models.
- Pythonic query builder instead of raw query strings.
- Document serialization and deserialization.
- Async support.
- Active ongoing development.

### Installation

```bash
pip install pyodmongo
```

### Contributing

Contributions are welcomed via the GitHub repository:

- https://github.com/mauro-andre/pyodmongo

### License

PyODMongo is licensed under the MIT License.

---

## Getting Started

Source: https://pyodmongo.dev/getting_started/

This guide covers creating an engine, defining a model, saving data, and reading data.

### Creating Engine

Create a `DbEngine` to connect to MongoDB.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"


box = Product(name="Box", price="5.99", is_available=True)

response: DbResponse = engine.save(box)
```

Replace `mongodb://localhost:27017` and `my_db` with your actual connection string and database name.

When creating an engine, you can pass `tz_info`. That sets the default timezone for `find_one` and `find_many` unless a per-call `tz_info` overrides it.

### Defining a Model

Models inherit from `DbModel` and must define `_collection` as a `ClassVar[str]`.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"


box = Product(name="Box", price="5.99", is_available=True)

response: DbResponse = engine.save(box)
```

### Saving Data

Use `save()` on the engine.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"


box = Product(name="Box", price="5.99", is_available=True)

response: DbResponse = engine.save(box)
```

### Reading from the Database

Use `find_one()` on the engine.

```python
from pyodmongo import DbEngine, DbModel
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"

query = Product.name == "Box"
box: Product = engine.find_one(Model=Product, query=query)
```

---

## DbModel

Source: https://pyodmongo.dev/db_model/

`DbModel` is the base class used to model MongoDB collections. A class inheriting from `DbModel` represents a collection and should declare `_collection`.

```python
from pyodmongo import DbModel
from typing import ClassVar


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"
```

### Inherited Attributes

When a class inherits from `DbModel`, it automatically gains metadata fields.

#### `id: Id`

- Unique identifier for the document.
- Automatically generated if not provided.
- Stored as MongoDB `ObjectId` under the hood.
- Accepts either `str` or `ObjectId` inputs and converts them as needed.
- Equivalent to MongoDB `_id`.

#### `created_at: datetime`

- Managed entirely by PyODMongo.
- Set automatically when the document is first created.

#### `updated_at: datetime`

- Managed entirely by PyODMongo.
- Updated automatically when the document changes.

### Relationships

PyODMongo supports both reference relationships and embedded documents.

#### Reference Relationships

Reference relationships store document references by identifier.

```python
from pyodmongo import DbModel, Id
from typing import ClassVar


class User(DbModel):
	username: str
	password: str
	_collection: ClassVar = "users"


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	user: User | Id
	_collection: ClassVar = "products"
```

`user` may be either a `User` instance or an `Id`. Lists of references are also supported, for example `list[User | Id]`.

#### Embedded Documents

Embedded documents are modeled as nested objects.

```python
from pyodmongo import DbModel, MainBaseModel
from typing import ClassVar


class Address(MainBaseModel):
	street: str
	city: str
	state: str
	zip_code: str


class User(DbModel):
	username: str
	password: str
	address: Address
	_collection: ClassVar = "users"
```

Notes:

- `MainBaseModel` is preferred over plain Pydantic `BaseModel` for nested elements because some search methods such as `$elemMatch` require it.
- You can also embed data from other `DbModel` objects when you want to keep current values in the parent document.

#### Leveraging Relationships

These relationship types let you model linked or nested structures according to application needs.

---

## Save

Source: https://pyodmongo.dev/save/

### Save

`save` exists on `DbEngine` and is used to create or update documents.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"


box = Product(name="Box", price="5.99", is_available=True)

response: DbResponse = engine.save(box)
```

If `save` creates a new document, the object instance receives `id`, `created_at`, and `updated_at`.

### Arguments

- `obj: Any`: object to save.
- `query: ComparisonOperator | LogicalOperator = None`: query used to choose documents to update. If omitted, PyODMongo updates the document whose `_id` matches `obj.id`. If `obj` has no `id`, a new document is created.
- `raw_query: dict = None`: raw MongoDB-compatible query for updates.
- `upsert: bool = True`: insert when no match exists. If `False`, only update existing matches.

Warnings and notes:

- If `query` is provided, `raw_query` is ignored.
- Internally, PyODMongo uses `update_many` with `upsert=True`, so it can add or update one or multiple documents.

### Save All

`save_all` stores a mixed list of objects, grouped by collection.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"


class User(DbModel):
	name: str
	email: str
	password: str
	_collection: ClassVar = "users"


obj_list = [
	Product(name="Box", price="5.99", is_available=True),
	Product(name="Ball", price="6.99", is_available=True),
	User(name="John", email="john@email.com", password="john_pwd"),
]

response: dict[str, DbResponse] = engine.save_all(obj_list)
```

### Save Responses

`save` returns `DbResponse`.

`save_all` returns `dict[str, DbResponse]`, keyed by collection name.

#### `DbResponse` Attributes

- `acknowledged: bool`
- `deleted_count: int`
- `inserted_count: int`
- `matched_count: int`
- `modified_count: int`
- `upserted_count: int`
- `upserted_ids: dict[int, Id]`

These fields report how many documents were inserted, matched, updated, deleted, or upserted.

---

## Find

Source: https://pyodmongo.dev/find/

### Find One

`find_one` exists on `DbEngine` and retrieves one object matching the criteria.

```python
from pyodmongo import DbEngine, DbModel
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"

query = Product.name == "Box"
box: Product = engine.find_one(Model=Product, query=query)
```

#### Arguments

- `Model: DbModel`: model used to form the returned object.
- `query: ComparisonOperator | LogicalOperator`: filter query.
- `raw_query: dict`: raw MongoDB-compatible query.
- `sort: SortOperator`: sort tuples using `1` for ascending and `-1` for descending.
- `raw_sort: dict`: raw MongoDB-compatible sort.
- `populate: bool`: populate relationship fields instead of leaving only `id` values.
- `as_dict: bool`: return plain dictionaries instead of instantiated objects.
- `tz_info: timezone`: timezone to apply to `datetime` fields.

If `query` is passed, `raw_query` is ignored.

### Find Many

`find_many` is similar to `find_one`, but returns multiple objects.

```python
from pyodmongo import DbEngine, DbModel
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"

query = (Product.price >= 50) & (Product.price < 100)

products: list[Product] = engine.find_many(Model=Product, query=query)
```

It accepts the same main arguments as `find_one`, plus pagination controls.

#### Pagination Arguments

- `paginate: bool`: return a paginated response instead of a plain list.
- `current_page: int`: page to fetch when `paginate=True`.
- `docs_per_page: int`: max documents per page when `paginate=True`.

#### Paginate

When `paginate=True`, the result is a `ResponsePaginate` object with:

- `current_page: int`
- `page_quantity: int`
- `docs_quantity: int`
- `docs: list[Any]`

Example:

```python
from pyodmongo import DbEngine, DbModel, ResponsePaginate
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"

query = (Product.price >= 50) & (Product.price < 100)

response: ResponsePaginate = engine.find_many(
	Model=Product, query=query, paginate=True, current_page=2, docs_per_page=100
)
```

### Populate

Populate automatically resolves references, including nested references and reference lists.

Behavior:

- `populate=True` on `find_one` or `find_many` populates all references in the returned object.
- Referenced objects can themselves be recursively populated.
- Reference lists are populated as well.

PyODMongo uses MongoDB aggregation under the hood to implement this efficiently.

---

## Delete

Source: https://pyodmongo.dev/delete/

### Delete

`delete` exists on `DbEngine` and removes documents matching a query.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"

query = Product.price <= 100

response: DbResponse = engine.delete(Model=Product, query=query)
```

#### Arguments

- `Model: DbModel`: model whose collection will be queried.
- `query: ComparisonOperator | LogicalOperator`: selection criteria.
- `raw_query: dict`: optional raw MongoDB query.

Warning:

- Internally, `delete` uses MongoDB `delete_many`, so all matching documents are removed.

### Delete One

There is no separate `delete_one` method. To delete only one matching document, pass `delete_one=True` to `delete`.

```python
from pyodmongo import DbEngine, DbModel, DbResponse
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"

query = Product.name == "Box"

response: DbResponse = engine.delete(
	Model=Product, query=query, delete_one=True
)
```

### Delete Response

`delete` returns `DbResponse`, with the same status fields documented for save responses:

- `acknowledged: bool`
- `deleted_count: int`
- `inserted_count: int`
- `matched_count: int`
- `modified_count: int`
- `upserted_count: int`
- `upserted_ids: dict[int, Id]`

---

## Query Operators

Source: https://pyodmongo.dev/query_operators/

PyODMongo query building is centered around operators used by `find_many`, `find_one`, `delete`, and `save` on `DbEngine`.

### Equal

```python
from pyodmongo import DbEngine, DbModel
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(DbModel):
	name: str
	price: float
	is_available: bool
	_collection: ClassVar = "products"


query = Product.name == "Box"
box: Product = engine.find_one(Model=Product, query=query)
```

Equivalent MongoDB filter:

```python
{name: {$eq: "Box"}}
```

### Greater Than

```python
query = Product.price > 10
```

Equivalent:

```python
{price: {$gt: 10}}
```

### Greater Than Equal

```python
query = Product.price >= 10
```

Equivalent:

```python
{price: {$gte: 10}}
```

### In

```python
from pyodmongo.queries import in_

query = in_(Product.name, ["Ball", "Box", "Toy"])
```

Equivalent:

```python
{name: {$in: ["Ball", "Box", "Toy"]}}
```

### Lower Than

```python
query = Product.price < 10
```

Equivalent:

```python
{price: {$lt: 10}}
```

### Lower Than Equal

```python
query = Product.price <= 10
```

Equivalent:

```python
{price: {$lte: 10}}
```

### Not Equal

```python
query = Product.name != "Box"
```

Equivalent:

```python
{name: {$ne: "Box"}}
```

### Not In

```python
from pyodmongo.queries import nin

query = nin(Product.name, ["Ball", "Box", "Toy"])
```

Equivalent:

```python
{name: {$nin: ["Ball", "Box", "Toy"]}}
```

### And

```python
query = (Product.price > 10) & (Product.price <= 50)
```

Equivalent:

```python
{$and: [{price: {$gt: 10}}, {price: {$lte: 50}}]}
```

### Or

```python
query = (Product.name == "Box") | (Product.price == 100)
```

Equivalent:

```python
{$or: [{name: {$eq: "Box"}}, {price: {$eq: 100}}]}
```

### Nor

```python
from pyodmongo.queries import nor, eq

query = nor(eq(Product.name, "Box"), eq(Product.price, 100))
```

Equivalent:

```python
{$nor: [{name: {$eq: "Box"}}, {price: {$eq: 100}}]}
```

### Elem Match

```python
from pyodmongo import DbEngine, MainBaseModel, DbModel
from typing import ClassVar
from pyodmongo.queries import elem_match

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Product(MainBaseModel):
	name: str
	price: float
	is_available: bool


class Order(DbModel):
	code: str
	products: list[Product]
	_collection: ClassVar = "orders"


query = elem_match(Product.name == "Box", Product.price == 50, field=Order.products)
box: Product = engine.find_one(Model=Product, query=query)
```

Equivalent:

```python
{$products: {$elemMatch: {name: "Box", price: 50}}}
```

### Sort

```python
from pyodmongo.queries import sort

query = Product.price >= 10
my_sort = sort((Product.name, 1), (Product.price, -1))
box: Product = engine.find_one(Model=Product, query=query, sort=my_sort)
```

Equivalent:

```python
{name: 1, price: -1}
```

---

## Use with FastAPI

Source: https://pyodmongo.dev/fastapi/

PyODMongo works naturally with FastAPI because it is built on Pydantic.

```python
from fastapi import FastAPI, Request
from pyodmongo import DbModel, DbEngine
from pyodmongo.queries import mount_query_filter
from typing import ClassVar

app = FastAPI()
engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class MyModel(DbModel):
	attr1: str
	attr2: str
	attr3: int
	_collection: ClassVar = "my_model"


@app.get("/", response_model=list[MyModel])
def get_route(request: Request):
	query, sort = mount_query_filter(
		Model=MyModel,
		items=request.query_params._dict,
		initial_comparison_operators=[],
	)
	return engine.find_many(Model=MyModel, query=query, sort=sort)
```

### `mount_query_filter`

This function is designed to convert query-string dictionaries into PyODMongo query operators.

Parameters:

- `Model: DbModel`
- `items: dict`
- `initial_comparison_operators: list[QueryOperator]`

Return behavior:

- Returns a query using logical `and` across all recognized items.

### Example Usage

Request URL example:

```text
http://localhost:8000/?attr1_eq=value_1&attr2_in=%5B'value_2',%20'value_3'%5D&attr3_gte=10&_sort=%5B%5B'attr1',%201%5D,%20%5B'attr2',%20-1%5D%5D
```

Equivalent `request.query_params._dict`:

```python
{
	"attr1_eq": "value_1",
	"attr2_in": "['value_2', 'value_3']",
	"attr3_gte": 10,
	"_sort": "[['attr1', 1], ['attr2', -1]]",
}
```

Keys are expected in the format `attribute_operator`.

Supported operators documented on the page:

- `eq`
- `gt`
- `gte`
- `in`
- `lt`
- `lte`
- `ne`
- `nin`
- `sort`

---

## Indexes

Source: https://pyodmongo.dev/indexes/

Indexes can be defined directly on fields or through explicit PyMongo `IndexModel` entries.

### Simple Index Creation

Use `Field(...)` flags.

```python
from pyodmongo import DbModel, Field
from typing import ClassVar


class Product(DbModel):
	name: str = Field(index=True)
	code: str = Field(index=True, unique=True)
	description: str = Field(text_index=True, default_language="english")
	price: float
	product_type: str
	is_available: bool
	_collection: ClassVar = "products"
```

Field options:

- `index: bool`: create a standard index on the field.
- `unique: bool`: enforce uniqueness for the indexed field.
- `text_index: bool`: include the field in text indexes.
- `default_language: str`: default language for MongoDB text search.

### Advanced Index Creation

Use class-level `_indexes` with PyMongo `IndexModel`.

```python
from pyodmongo import DbModel
from pymongo import IndexModel, ASCENDING, DESCENDING
from typing import ClassVar


class Product(DbModel):
	name: str
	code: str
	description: str
	price: float
	product_type: str
	is_available: bool
	_collection: ClassVar = "products"
	_indexes: ClassVar = [
		IndexModel([("name", ASCENDING), ("price", DESCENDING)], name="name_and_price"),
		IndexModel([("product_type", DESCENDING)], name="product_type"),
	]
```

PyODMongo follows PyMongo index structure rules for custom index definitions.

---

## Aggregation

Source: https://pyodmongo.dev/aggregation/

PyODMongo supports aggregation by allowing you to define `_pipeline` on a model. That pipeline is executed when `find_one` or `find_many` is called for that model.

```python
from pyodmongo import DbModel, DbEngine, Id
from typing import ClassVar

engine = DbEngine(mongo_uri="mongodb://localhost:27017", db_name="my_db")


class Customer(DbModel):
	name: str
	email: str
	_collection: ClassVar = "customers"


class Order(DbModel):
	customer: Customer | Id
	value: float
	_collection: ClassVar = "orders"


class OrdersByCustomers(DbModel):
	count: int
	total_value: float
	_collection: ClassVar = "orders"
	_pipeline: ClassVar = [
		{
			"$group": {
				"_id": "$customer",
				"count": {"$count": {}},
				"total_value": {"$sum": "$value"},
			}
		}
	]

result: list[OrdersByCustomers] = engine.find_many(Model=OrdersByCustomers)
```

Notes:

- PyODMongo already uses aggregation under the hood for `find` and `find_one`.
- The `query` parameter is converted into a `$match` stage and inserted as the first stage of the pipeline.
- You can combine `query` with `_pipeline`.
- The aggregation output must align with the fields declared on the target class.

---

## Contributing

Source: https://pyodmongo.dev/contributing/

PyODMongo is open source and accepts community contributions.

### How Can You Contribute?

- Report issues on GitHub.
- Submit pull requests for fixes, features, and improvements.
- Improve documentation, examples, or typos.
- Write and run tests to improve reliability.

### Code of Conduct

The project follows a Code of Conduct:

- https://github.com/mauro-andre/pyodmongo/blob/master/code_of_conduct.md

---

## Release Notes

Source: https://pyodmongo.dev/release_notes/

The release notes page currently documents releases from `v1.1.0` through `v1.7.0`.

### v1.7.0 - 2025-08-19

- No paginate limit stage.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.6...1.7.0

### v1.6.6 - 2025-07-16

- Fix pipeline order in `mount_base_pipeline`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.5...1.6.6

### v1.6.5 - 2025-04-24

- Fix deprecation warning for Pydantic `model_fields` usage.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.4...1.6.5

### v1.6.4 - 2025-04-24

- `mount_base_pipeline` with skip and limit when pipeline.
- New contributor: `@PedroBergamin`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.3...1.6.4

### v1.6.3 - 2025-03-27

- Refactor skip and limit stages in pipeline.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.2...1.6.3

### v1.6.2 - 2025-02-28

- Fix `None` handling in mounted query filters.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.1...1.6.2

### v1.6.1 - 2025-02-24

- Fix `consolidate_dict` and `DbField` comparison behavior for `Decimal` and `DbDecimal`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.6.0...1.6.1

### v1.6.0 - 2025-02-23

- Introduce `DbDecimal`, mapping Python `Decimal` to MongoDB `Decimal128`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.5.1...1.6.0

### v1.5.1 - 2025-02-19

- `save` and `save_all` add `populate` argument.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.5.0...1.5.1

### v1.5.0 - 2025-02-18

- Fix replacement of empty dicts in `DbModel`.
- Add pipeline support in `find_one` and `find_many`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.6...1.5.0

### v1.4.6 - 2025-01-16

- Fix pipeline `$set` stage index and empty array behavior when unwind index is null.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.5...1.4.6

### v1.4.5 - 2025-01-15

- Add sort stage before group stage and unset after nested group processing.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.4...1.4.5

### v1.4.4 - 2025-01-14

- Fix group stage in pipeline.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.3...1.4.4

### v1.4.3rc3 - 2024-11-22

- Refactor resolve reference pipeline.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.3rc2...1.4.3rc3

### v1.4.3 - 2024-11-29

- Same code as `v1.4.3rc3`.
- Enhance `DbModel` initialization and aggregate pipeline construction.
- Improve test coverage.
- Update requirements.
- Refactor resolve reference pipeline.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.2...1.4.3

### v1.4.3rc2 - 2024-11-21

- Improve compatibility with Pydantic 2.10 in the `PyOdmongoMeta.__getattr__` path.
- Improve test coverage.
- Update requirements.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.3rc1...1.4.3rc2

### v1.4.3rc1 - 2024-11-20

- Refactor `DbModel` initialization and MongoDB aggregate pipeline construction.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.2...1.4.3rc1

### v1.4.2 - 2024-11-09

- Fix nested unique index behavior.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.0...1.4.2

### v1.4.1 - 2024-10-07

- Nested persisted object with index creation.
- Fix duplicate text index name.
- Fix index creation after nested attribute access.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.3.0...1.4.0

### v1.4.0rc3 - 2024-10-07

- Fix index creation after nested attribute access.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.4.0rc2...1.4.0rc3

### v1.4.0rc2 - 2024-10-07

- Release listed with no detailed notes on the page.

### v1.4.0rc1 - 2024-10-07

- Release listed with no detailed notes on the page.

### v1.3.0 - 2024-10-03

- Add optional upsert support to `save`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.2.2...1.3.0

### v1.2.2 - 2024-07-29

- Fix `DbModel` initialization of empty lists.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.2.1...1.2.2

### v1.2.1 - 2024-07-18

- Fix nested attribute bug in `db_field_info`.
- New contributor: `@patrickpasquini`.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.2.0...1.2.1

### v1.2.0 - 2024-07-02

- Add logical `and` and `or` handling to mounted query operators.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.1.2...1.2.0

### v1.1.2 - 2024-06-26

- Remove stray prints.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.1.1...1.1.2

### v1.1.1 - 2024-06-26

- Fix `KeyError` in `DbModel` initialization when using a serialized class.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.1.0...1.1.1

### v1.1.0rc2 - 2024-06-25

- Refine empty-list handling during `DbModel` initialization.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.1.0rc1...1.1.0rc2

### v1.1.0 - 2024-06-25

- Sync `find_many` thread pool executor changes.
- Refactor reference pipeline.
- Refine empty-list handling during `DbModel` initialization.
- Full changelog: https://github.com/mauro-andre/pyodmongo/compare/1.0.1...1.1.0

---

## Site Map Snapshot

Source: https://pyodmongo.dev/sitemap.xml

English pages discovered from the sitemap:

- https://pyodmongo.dev/
- https://pyodmongo.dev/aggregation/
- https://pyodmongo.dev/contributing/
- https://pyodmongo.dev/db_model/
- https://pyodmongo.dev/delete/
- https://pyodmongo.dev/fastapi/
- https://pyodmongo.dev/find/
- https://pyodmongo.dev/getting_started/
- https://pyodmongo.dev/indexes/
- https://pyodmongo.dev/query_operators/
- https://pyodmongo.dev/release_notes/
- https://pyodmongo.dev/save/
