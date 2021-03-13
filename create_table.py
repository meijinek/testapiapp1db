from flask import Flask
from flask_dynamo import Dynamo
from boto3.session import Session


boto_sess = Session(profile_name="dynamodb-adminuser")


app = Flask(__name__)
app.config['DYNAMO_TABLES'] = [
    {
         'TableName':  'ItemTable',
         'AttributeDefinitions': [{
             'AttributeName': 'name',
             'AttributeType': 'S'
         }],
         'KeySchema': [{
             'AttributeName': 'name',
             'KeyType': 'HASH'
         }],
         'BillingMode': 'PAY_PER_REQUEST'
    }
]
app.config['DYNAMO_SESSION'] = boto_sess

dynamo = Dynamo(app)

with app.app_context():
    dynamo.create_all()
