Working environment is project root. Business logic goes into src/. So make sure to import from "src.".

We use pydantic for data validation. We use type hinting throughout. Always annotate variables, arguments and return types.

We use pytest for testing. All tests go in tests/.
Use the mocker fixture to mock in tests. 