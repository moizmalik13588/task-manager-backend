from fastapi import HTTPException

def raise_not_found_error(resource_name: str, resource_id: int):
    return HTTPException(
        status_code=404,
        detail= f"{resource_name} with this id: {resource_id} is not found"
    )