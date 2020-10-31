# coding: utf-8

import os

import motor.motor_asyncio
import pymongo
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

MONGO_CONNECTION_STRING = os.environ['MONGO_CONNECTION_STRING']

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_CONNECTION_STRING)
db = client['hack2020']

path = os.path.dirname(__file__)
static_path = os.path.join(path, 'static')


app = FastAPI(
    title='Neuramark Metadata Service API',
    version='1.0.0',
    docs_url=None,
    redoc_url=None
)

app.mount('/static', StaticFiles(directory=static_path), name='static')


class Application(BaseModel):
    name: str
    hashed_password: str
    admin_email: str
    token: str


class UpdateData(BaseModel):
    name: str
    token: str


@app.on_event('startup')
async def startup_event():
    await db.applications.create_index('name', unique=True)


@app.post('/create_application')
async def create_application(application: Application):
    app_dict = application.dict()
    app_dict['password'] = app_dict.pop('hashed_password')
    try:
        result = await db.applications.insert_one(app_dict)
    except pymongo.errors.DuplicateKeyError:
        raise HTTPException(status_code=400, detail='Application already exist!')
    return {'application_id': str(result.inserted_id)}


@app.get('/get_application')
async def get_application(name: str):
    application = await db.applications.find_one({'name': name})
    if application is None:
        raise HTTPException(status_code=404, detail='Application not found!')
    application['_id'] = str(application['_id'])
    return application


@app.delete('/delete_application')
async def delete_application(name: str):
    result = await db.applications.delete_many({'name': name})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail='Application not found!')
    return {'ok': True}


@app.post('/update_token')
async def update_token(data: UpdateData):
    result = await db.applications.update_one({'name': data.name}, {'$set': {'token': data.token}})
    if not result.modified_count:
        raise HTTPException(status_code=404, detail='Application not found!')
    return {'ok': True}


@app.get('/docs', include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f'{app.title} - Swagger UI',
        swagger_js_url='/static/js/swagger-ui-bundle.js',
        swagger_css_url='/static/css/swagger-ui.css'
    )
