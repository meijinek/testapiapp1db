from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_dynamo import Dynamo
from boto3.session import Session
from helpers import decimal_to_float, convert_to_decimal

# Elastic Beanstalk requires the Flask instance to be called application
application = Flask(__name__)
api = Api(application)

#  setting up the dynamodb table
#  no profile_name for elasticbeanstalk, will use an IAM role
boto_sess = Session(region_name="eu-west-2")

application.config['DYNAMO_TABLES'] = [
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
application.config['DYNAMO_SESSION'] = boto_sess

dynamo = Dynamo(application)

with application.app_context():
    dynamo.create_all()


class Item(Resource):
    #  parses json in incoming http request
    #  we only want price in the json body
    #  name is provided in the route
    parser = reqparse.RequestParser()
    parser.add_argument(
            'price',
            type=float,
            required=True,
            help="Cannot be left blank"
        )

    @classmethod
    def find_by_name(cls, name):
        result = dynamo.tables['ItemTable'].get_item(Key={
            'name': name
            }
        )
        if 'Item' in result:
            return decimal_to_float(result['Item'])

    @classmethod
    def insert(cls, item):
        result = dynamo.tables['ItemTable'].put_item(Item={
            'name': item['name'],
            'price': convert_to_decimal(item['price'])
            }
        )

    @classmethod
    def update(cls, item):
        result = dynamo.tables['ItemTable'].update_item(Key={
            'name': item['name']
            },
            UpdateExpression='SET price = :p',
            ExpressionAttributeValues={
                ':p': convert_to_decimal(item['price'])
            }
        )
        print(result)

    def get(self, name):
        item = self.find_by_name(name)
        if item:
            return item
        return {'message': 'item not found'}

    def post(self, name):
        if self.find_by_name(name):
            return {'message': f'an item with name {name} already exists'}, 400
        data = Item.parser.parse_args()
        item = {'name': name, 'price': data['price']}
        Item.insert(item)

        try:
            Item.insert(item)
        except:
            return {'message': 'an error occurred inserting the item.'}, 500

        return item

    def delete(self, name):
        result = dynamo.tables['ItemTable'].delete_item(Key={
                'name': name
            },
            ReturnValues='ALL_OLD'
        )
        # Attributes key will be returned by boto3 if the item exists in the table
        if 'Attributes' in result:
            return {'message': 'item deleted'}
        return {'message': 'item does not exist'}

    def put(self, name):
        data = Item.parser.parse_args()
        item = self.find_by_name(name)
        updated_item = {'name': name, 'price': data['price']}
        if item is None:
            try:
                Item.insert(updated_item)
            except:
                return {'message': 'an error occurred inserting the item.'}, 500
        else:
            try:
                Item.update(updated_item)
            except:
                return {'message': 'an error occurred inserting the item.'}, 500
        return updated_item


class ItemList(Resource):
    def get(self):
        result = dynamo.tables['ItemTable'].scan(Limit=100)
        if len(result['Items']) == 0:
            return {'message': 'no items in the database found'}
        return decimal_to_float(result['Items'])


api.add_resource(Item, '/item/<string:name>')
api.add_resource(ItemList, '/items')


application.run()
