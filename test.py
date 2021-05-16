
import collections
import math
import json
from pymongo import collation
from pymongo.message import _CursorAddress
import telebot
from telebot import types
import pymongo

import time

# initialize configs
with open('config.json') as f:
    config = json.load(f)


class Database:
    def __init__(self, connection_string, db_name):
        # initialize mongodb
        self.db_name = db_name
        self.dbclient = pymongo.MongoClient(connection_string)
        self.db = self.dbclient[config['db_name']]

    def convert_id(self, user_id):
        items_id = []
        for item in self.get_list():
            items_id.append(item['_id'])
        return items_id[user_id]

    def get_list(self):
        collection = self.db[self.db_name]
        return collection.find({})

    def get(self, id):
        collection = self.db[self.db_name]
        return collection.find_one({'_id': self.convert_id(id)})
    
    def modify(self, id, field, value):
        collection = self.db[self.db_name]
        collection.find_one_and_update({'_id': self.convert_id(id)}, {"$set": {field: value}})

    def add(self, value):
        collection = self.db[self.db_name]
        collection.insert_one(value)

    def remove(self, id):
        self.db[self.db_name].delete_one({'_id': self.convert_id(id)})
      
class FuelManager:
    def __init__(self):
        self.fueldb = Database(config['connection_string'], 'fuel')
        self.carsdb = Database(config['connection_string'], 'cars')
    
    def get_fuel(self):
        return self.fueldb.get_list()[0]['fuel']

    def add(self, value):
        current_value = self.get_fuel()
        self.fueldb.modify(0, 'fuel', current_value + value)

    def remove(self, value):
        current_value = self.get_fuel()
        new_value = current_value - value

        if new_value < 0:
            new_value = 0
        
        self.fueldb.modify(0, 'fuel', new_value)

    def add_to_car(self, car_id, value):
        car_fuel = self.carsdb.get(car_id)['fuel']
        all_fuel = self.get_fuel()

        if all_fuel >= value:
            car_fuel += value
        else:
            car_fuel += all_fuel

        self.remove(value)
        self.carsdb.modify(car_id, 'fuel', car_fuel)
            

fuel_manager = FuelManager()

fuel_manager.add_to_car(0, 200)