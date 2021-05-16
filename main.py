# pip install dnspython
# pip install pyTelegramBotAPI

import math
import json
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
   
class Car:
    def __init__(self, car_type):
        self.type = car_type
        self.mark = None
        self.model = None
        self.number = None
        self.odometr = None
        self.vin_code = None
        self.engine_capacity = None
        self.power = None
        self.manufacture_year = None
        self.fuel = 0

class CarManager:
    def __init__(self):
        self.db = Database(config['connection_string'], 'cars')

    def add(self, car):
        self.db.add({
            'type': car.type,
            'mark': car.mark,
            'model': car.model,
            'number': car.number,
            'vin_code': car.vin_code,
            'engine_capacity': car.engine_capacity,
            'power': car.power,
            'manufacture_year': car.manufacture_year,
            'odometr': car.odometr,
            'fuel': car.fuel
        })

    def remove(self, id):
        self.db.remove(id)

    def get_list(self):
        return self.db.get_list()

class FuelManager:
    def __init__(self, carsdb):
        self.fueldb = Database(config['connection_string'], 'fuel')
        self.carsdb = carsdb
    
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

class DialogManager:
    def __init__(self):
        self.car_manager = CarManager()
        self.fuel_manager = FuelManager(self.car_manager.db)
        self.user_dict = {}

        # initialize bot
        self.bot = telebot.TeleBot(config['api_key'])

        self.main_dialog()

    def start(self):
        self.bot.polling()

    def default_message(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=1)
        btn1 = types.KeyboardButton('Облік автотранспорту')
        btn2 = types.KeyboardButton('Облік залишків палива')
        btn3 = types.KeyboardButton('Калькулятори')
        markup.add(btn1, btn2, btn3)
        self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)

    def car_dialog(self, message):
        def proccess_car_delete(message):
            try:
                car_id = int(message.text)
                self.car_manager.remove(car_id)
                self.bot.send_message(message.chat.id, 'Готово')
            except:
                self.bot.send_message(message.chat.id, 'Невірний id')
            
            self.default_message(message)

        def process_car_type_step(message):
            car = Car(message.text)

            if message.text != 'Інша техніка':
                msg = self.bot.send_message(message.chat.id, 'Марка автомобіля')
                self.bot.register_next_step_handler(msg, process_car_mark_step, car)
            else:
                msg = self.bot.send_message(message.chat.id, 'Введіть тип автомобіля')
                self.bot.register_next_step_handler(msg, process_car_type_step_2, car)

        def process_car_type_step_2(message, car):
            car.type = message.text
            msg = self.bot.send_message(message.chat.id, 'Модель автомобіля')
            self.bot.register_next_step_handler(msg, process_car_mark_step, car)

        def process_car_mark_step(message, car):
            car.mark = message.text
            msg = self.bot.send_message(message.chat.id, 'Модель автомобіля')
            self.bot.register_next_step_handler(msg, process_car_model_step, car)

        def process_car_model_step(message, car):
            car.model = message.text
            msg = self.bot.send_message(message.chat.id, 'Регістраційний номер')
            self.bot.register_next_step_handler(msg, process_car_number_step, car)

        def process_car_number_step(message, car):
            car.number = message.text
            msg = self.bot.send_message(message.chat.id, 'VIN код, номер шасі (кузова, рами)')
            self.bot.register_next_step_handler(msg, process_car_vin_code_step, car)
            
        def process_car_vin_code_step(message, car):
            car.vin_code = message.text
            msg = self.bot.send_message(message.chat.id, 'Одометр (км)')
            self.bot.register_next_step_handler(msg, process_car_odometr_step, car)

        def process_car_odometr_step(message, car):
            car.odometr = message.text
            
            msg = self.bot.send_message(message.chat.id, 'Об’єм двигуна (л)')
            self.bot.register_next_step_handler(msg, process_car_engine_capacity_step, car)

        def process_car_engine_capacity_step(message, car):
            car.engine_capacity = message.text
            
            msg = self.bot.send_message(message.chat.id, 'Потужність (к. с.)')
            self.bot.register_next_step_handler(msg, process_car_power_step, car)

        def process_car_power_step(message, car):
            car.power = message.text
            
            msg = self.bot.send_message(message.chat.id, 'Рік випуску')
            self.bot.register_next_step_handler(msg, process_car_year_step, car)

        def process_car_year_step(message, car):
            car.manufacture_year = message.text
            
            self.bot.send_message(message.chat.id, 'Готово')

            self.default_message(message)

            self.car_manager.add(car)

        if message.text == 'Облік автотранспорту':
            markup = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
            btn1 = types.KeyboardButton('Додати автомобіль')
            btn2 = types.KeyboardButton('Видалити автомобіль')
            btn3 = types.KeyboardButton('Переглянути список всіх автомобілів')
            btn4 = types.KeyboardButton('Назад')
            markup.add(btn1, btn2, btn3, btn4)
            self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)    
            return True

        if message.text == 'Додати автомобіль':
            markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
            btn1 = types.KeyboardButton('Зерновоз')
            btn2 = types.KeyboardButton('Самосвал')
            btn3 = types.KeyboardButton('Фургон')
            btn4 = types.KeyboardButton('Трактор')
            btn5 = types.KeyboardButton('Косилка')
            btn6 = types.KeyboardButton('Сіялка')
            btn7 = types.KeyboardButton('Комбайн')
            btn8 = types.KeyboardButton('Інша техніка')
            btn9 = types.KeyboardButton('Інша техніка')

            markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
            self.bot.send_message(message.chat.id, 'Виберіть тип', reply_markup=markup)
            
            self.bot.register_next_step_handler(message, process_car_type_step)
            return True

        if message.text == 'Видалити автомобіль':

            self.bot.send_message(message.chat.id, 'Введіть id:')

            self.bot.register_next_step_handler(message, proccess_car_delete)
            return True

        if message.text == 'Переглянути список всіх автомобілів':
            if not message.chat.id in self.user_dict:
                self.user_dict[message.chat.id] = 0

            cars = self.car_manager.get_list()
            show_cars = []
            for i in range(0, 3):
                try:
                    show_cars.append(cars[i])
                except:
                    break
            
            if len(show_cars) == 0:
                self.bot.send_message(message.chat.id, 'В парку немає техніки')
                return True

            pages_count = str(math.trunc(cars.collection.count_documents({}) / 3 + 1))

            markup = types.InlineKeyboardMarkup()
            markup.row_width = 3
            markup.add(types.InlineKeyboardButton('<---', callback_data='cb_prev'),
                                    types.InlineKeyboardButton('--->', callback_data='cb_next'),
                                    types.InlineKeyboardButton('Назад', callback_data='cb_exit'))

            index = 0
            text = ''
            for car in show_cars:
                text += '---------\n'
                text += 'id: ' + str(index) + '\n'
                
                text += 'Тип автомобіля: ' + car['type'] + '\n'
                text += 'Марка: ' + car['mark'] + '\n'
                text += 'Модель: ' + car['model'] + '\n'
                text += 'Регістраційний номер: ' + car['number'] + '\n'
                text += 'VIN код, номер шасі (кузова, рами): ' + car['vin_code'] + '\n'
                text += 'Об’єм двигуна (л): ' + car['engine_capacity'] + '\n'
                text += 'Потужність (к. с.): ' + car['power'] + '\n'
                text += 'Рік випуску: ' + car['manufacture_year'] + '\n'
                text += 'Одометр: ' + car['odometr'] + ' км\n'
                text += 'Паливо: ' + str(car['fuel']) + ' л\n'
                index += 1
            text += '---------\n'
            text += 'Сторінка 1/' + pages_count
            
            self.bot.send_message(message.chat.id, text, reply_markup=markup)
            return True

        return False 
        
    def calculator_dialog(self, message):
        if message.text == 'Калькулятори':
            markup = types.ReplyKeyboardMarkup(row_width=1)
            btn1 = types.KeyboardButton('Розрахунок розходу та вартості палива')
            btn2 = types.KeyboardButton('Розрахунок середнього розходу палива')
            btn3 = types.KeyboardButton('Розрахунок залишків палива')
            btn4 = types.KeyboardButton('Назад')
            markup.add(btn1, btn2, btn3, btn4)
            self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)
            return True

        if message.text == 'Розрахунок розходу та вартості палива':
            self.bot.send_message(message.chat.id, 'WIP')
            return True

        if message.text == 'Розрахунок середнього розходу палива':
            self.bot.send_message(message.chat.id, 'WIP')
            return True

        if message.text == 'Розрахунок залишків палива':
            self.bot.send_message(message.chat.id, 'WIP')
            return True

        return False
        
    def fuel_dialog(self, message):
        def process_add_fuel(message):
            try:
                fuel = int(message.text)
                self.fuel_manager.add(fuel)
                self.bot.send_message(message.chat.id, 'Готово')
            except:
                self.bot.send_message(message.chat.id, 'Невірна кількість')

            self.default_message(message)
            
        def process_remove_fuel(message):
            try:
                fuel = int(message.text)
                self.fuel_manager.remove(fuel)
                self.bot.send_message(message.chat.id, 'Готово')
            except:
                self.bot.send_message(message.chat.id, 'Невірна кількість')

            self.default_message(message)
            
        def process_add_fuel_to_car_step_1(message):
            car_id = int(message.text)
            self.bot.send_message(message.chat.id, "Введіть кількість палива:")
            self.bot.register_next_step_handler(message, process_add_fuel_to_car_step_2, car_id)

        def process_add_fuel_to_car_step_2(message, car_id):
            fuel = int(message.text)
            self.fuel_manager.add_to_car(car_id, fuel)
            self.bot.send_message(message.chat.id, 'Готово')
            self.default_message(message)

        if message.text == 'Облік залишків палива':
            markup = types.ReplyKeyboardMarkup(row_width=2)
            btn1 = types.KeyboardButton('Додати паливо до складу')
            btn2 = types.KeyboardButton('Додати паливо до техніки')
            btn3 = types.KeyboardButton('Видалити паливо з складу')
            btn4 = types.KeyboardButton('Перегляд залишків палива')
            btn5 = types.KeyboardButton('Назад')
            markup.add(btn1, btn2, btn3, btn4, btn5)
            self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)
            return True

        if message.text == 'Додати паливо до складу':
            self.bot.send_message(message.chat.id, "Введіть кількість палива:")
            self.bot.register_next_step_handler(message, process_add_fuel)
            return True
    
        if message.text == 'Додати паливо до техніки':
            self.bot.send_message(message.chat.id, "Введіть id техніки:")
            self.bot.register_next_step_handler(message, process_add_fuel_to_car_step_1)
            return True

        if message.text == 'Видалити паливо з складу':
            self.bot.send_message(message.chat.id, "Введіть кількість палива:")
            self.bot.register_next_step_handler(message, process_remove_fuel)
            return True

        if message.text == 'Перегляд залишків палива':
            self.bot.send_message(message.chat.id, f'Паливо на складі: {self.fuel_manager.get_fuel()} л.')
            return True
        
        return False

    def main_dialog(self):
        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_query(call):
            markup = types.InlineKeyboardMarkup()
            markup.row_width = 3
            markup.add(types.InlineKeyboardButton('<---', callback_data='cb_prev'),
                                    types.InlineKeyboardButton('--->', callback_data='cb_next'),
                                    types.InlineKeyboardButton('Назад', callback_data='cb_exit'))


            current_step = self.user_dict[call.message.chat.id]


            if call.data == 'cb_prev':
                if current_step >= 3:
                    current_step -= 3

            elif call.data == 'cb_next':
                if current_step <= self.car_manager.get_list().collection.count_documents({}) - 3:
                    current_step += 3
                else:
                    return

            elif call.data == 'cb_exit':
                del self.user_dict[call.message.chat.id]
                self.default_message(call.message)
                
                # self.bot.delete_message(call.message.chat.id, call.message.message_id)
                
            self.user_dict[call.message.chat.id] = current_step

            cars = self.car_manager.get_list()
            show_cars = []
            for i in range(current_step, current_step + 3):
                try:
                    show_cars.append(cars[i])
                except:
                    break

            current_page = str(math.trunc(current_step / 3 + 1))
            pages_count = str(math.trunc(cars.collection.count_documents({}) / 3 + 1))

            index = 0
            text = ''
            for car in show_cars:
                text += '---------\n'
                text += 'id: ' + str(index + current_step) + '\n'
                
                text += 'Тип автомобіля: ' + car['type'] + '\n'
                text += 'Марка: ' + car['mark'] + '\n'
                text += 'Модель: ' + car['model'] + '\n'
                text += 'Регістраційний номер: ' + car['number'] + '\n'
                text += 'VIN код, номер шасі (кузова, рами): ' + car['vin_code'] + '\n'
                text += 'Об’єм двигуна (л): ' + car['engine_capacity'] + '\n'
                text += 'Потужність (к. с.): ' + car['power'] + '\n'
                text += 'Рік випуску: ' + car['manufacture_year'] + '\n'
                text += 'Одометр: ' + car['odometr'] + ' км\n'
                text += 'Паливо: ' + str(car['fuel']) + ' л\n'

                index += 1

            
            text += '---------\n'
            text += f'Сторінка {current_page}/{pages_count}'

            try:
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            except:
                pass

        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            if not self.car_dialog(message):
                if not self.fuel_dialog(message):
                    if not self.calculator_dialog(message):
                        self.default_message(message)




dialog = DialogManager()
dialog.start()







