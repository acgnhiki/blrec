from http import HTTPStatus
from typing import Any, Dict, Union


from .schemas import ResponseMessage


ResponseDescriptor = Dict[Union[int, str], Dict[str, Any]]

not_found_responses: ResponseDescriptor = {
    HTTPStatus.NOT_FOUND.value: {
        'description': HTTPStatus.NOT_FOUND.phrase,
        'model': ResponseMessage,
    },
}

forbidden_responses: ResponseDescriptor = {
    HTTPStatus.FORBIDDEN.value: {
        'description': HTTPStatus.FORBIDDEN.phrase,
        'model': ResponseMessage,
    },
}

confict_responses: ResponseDescriptor = {
    HTTPStatus.CONFLICT.value: {
        'description': HTTPStatus.CONFLICT.phrase,
        'model': ResponseMessage,
    },
}

created_responses: ResponseDescriptor = {
    HTTPStatus.CREATED.value: {
        'description': HTTPStatus.CREATED.phrase,
        'model': ResponseMessage,
    },
}

accepted_responses: ResponseDescriptor = {
    HTTPStatus.ACCEPTED.value: {
        'description': HTTPStatus.ACCEPTED.phrase,
        'model': ResponseMessage,
    },
}
