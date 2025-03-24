# -*- coding: utf-8 -*-
import os
import sys
from fastapi import FastAPI
from fastapi.routing import APIRoute

for folders in [("app", "imports"), ("imports", ),
                ("app", "generated", "clients", "datago_file_client"),
                ("app", "generated", "clients", "datago_metadata_client")]:
    p = os.path.join(os.getcwd(), *folders)
    sys.path.append(p)


def use_route_names_as_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated API clients have simpler function
    names.

    Should be called only after all routes have been added.
    """
    for route in app.routes:
        print(route)
        if isinstance(route, APIRoute):
            route.operation_id = route.name