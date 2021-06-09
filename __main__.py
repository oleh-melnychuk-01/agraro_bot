# pip install dnspython
# pip install pyTelegramBotAPI
# pip install pymongo

import math
import json
import telebot
from telebot import types
import pymongo






class Database:
    def __init__(self, connection_string, db_name, config):
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

class Calculator:
    @staticmethod
    def fuel_consumption(distance, wasted_fuel):
        return wasted_fuel / distance * 100

    @staticmethod
    def fuel_cost(wasted_fuel, fuel_cost):
        return wasted_fuel / 100 * fuel_cost

    @staticmethod
    def fuel_consumption_per_hour(wasted_fuel, engine_power):
        return 0.7 * wasted_fuel * engine_power / 1000 * 0.84

class Vehicle:
    def __init__(self, vehicle_type):
        self.type = vehicle_type
        self.mark = None
        self.model = None
        self.number = None
        self.odometr = None
        self.vin_code = None
        self.engine_capacity = None
        self.power = None
        self.manufacture_year = None
        self.fuel = 0

class VehicleManager:
    def __init__(self, vehiclesdb):
        self.db = vehiclesdb

    def add(self, vehicle):
        self.db.add({
            'type': vehicle.type,
            'mark': vehicle.mark,
            'model': vehicle.model,
            'number': vehicle.number,
            'vin_code': vehicle.vin_code,
            'engine_capacity': vehicle.engine_capacity,
            'power': vehicle.power,
            'manufacture_year': vehicle.manufacture_year,
            'odometr': vehicle.odometr,
            'fuel': vehicle.fuel
        })

    def remove(self, id):
        self.db.remove(id)

    def get_list(self):
        return self.db.get_list()

class FuelManager:
    def __init__(self, vehiclesdb, fueldb):
        self.fueldb = fueldb
        self.vehiclesdb = vehiclesdb
    
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

    def add_to_vehicle(self, vehicle_id, value):
        vehicle_fuel = self.vehiclesdb.get(vehicle_id)['fuel']
        all_fuel = self.get_fuel()

        if all_fuel >= value:
            vehicle_fuel += value
        else:
            vehicle_fuel += all_fuel

        self.remove(value)
        self.vehiclesdb.modify(vehicle_id, 'fuel', vehicle_fuel)

class DialogManager:
    def __init__(self, config):
        self.vehiclesdb = Database(config['connection_string'], 'vehicles', config)
        self.fueldb = Database(config['connection_string'], 'fuel', config)
        self.vehicle_manager = VehicleManager(self.vehiclesdb)
        self.fuel_manager = FuelManager(self.vehiclesdb, self.fueldb)

        self.user_dict = {}

        # initialize bot
        self.bot = telebot.TeleBot(config['api_key'])

        self.main_dialog()

    def start(self):
        self.bot.polling()

    def default_message(self, message):
        markup = types.ReplyKeyboardMarkup(row_width=1)
        btn1 = types.KeyboardButton('🚜 Облік техніки')
        btn2 = types.KeyboardButton('⛽ Облік залишків палива')
        btn3 = types.KeyboardButton('🧮 Калькулятори')
        markup.add(btn1, btn2, btn3)
        self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)

    def vehicle_dialog(self, message):
        def proccess_vehicle_delete(message):
            try:
                vehicle_id = int(message.text)
                self.vehicle_manager.remove(vehicle_id)
                self.bot.send_message(message.chat.id, 'Готово')
            except:
                self.bot.send_message(message.chat.id, 'Невірний id')
            
            self.default_message(message)

        def process_vehicle_type_step(message):
            vehicle = Vehicle(message.text)

            if message.text != 'Інша техніка':
                msg = self.bot.send_message(message.chat.id, 'Марка техніки')
                self.bot.register_next_step_handler(msg, process_vehicle_mark_step, vehicle)
            else:
                msg = self.bot.send_message(message.chat.id, 'Введіть тип техніки')
                self.bot.register_next_step_handler(msg, process_vehicle_type_step_2, vehicle)

        def process_vehicle_type_step_2(message, vehicle):
            vehicle.type = message.text
            msg = self.bot.send_message(message.chat.id, 'Модель техніки')
            self.bot.register_next_step_handler(msg, process_vehicle_mark_step, vehicle)

        def process_vehicle_mark_step(message, vehicle):
            vehicle.mark = message.text
            msg = self.bot.send_message(message.chat.id, 'Модель техніки')
            self.bot.register_next_step_handler(msg, process_vehicle_model_step, vehicle)

        def process_vehicle_model_step(message, vehicle):
            vehicle.model = message.text
            msg = self.bot.send_message(message.chat.id, 'Регістраційний номер')
            self.bot.register_next_step_handler(msg, process_vehicle_number_step, vehicle)

        def process_vehicle_number_step(message, vehicle):
            vehicle.number = message.text
            msg = self.bot.send_message(message.chat.id, 'VIN код, номер шасі (кузова, рами)')
            self.bot.register_next_step_handler(msg, process_vehicle_vin_code_step, vehicle)
            
        def process_vehicle_vin_code_step(message, vehicle):
            vehicle.vin_code = message.text
            msg = self.bot.send_message(message.chat.id, 'Одометр (км)')
            self.bot.register_next_step_handler(msg, process_vehicle_odometr_step, vehicle)

        def process_vehicle_odometr_step(message, vehicle):
            vehicle.odometr = message.text
            
            msg = self.bot.send_message(message.chat.id, 'Об’єм двигуна (л)')
            self.bot.register_next_step_handler(msg, process_vehicle_engine_capacity_step, vehicle)

        def process_vehicle_engine_capacity_step(message, vehicle):
            vehicle.engine_capacity = message.text
            
            msg = self.bot.send_message(message.chat.id, 'Потужність (к. с.)')
            self.bot.register_next_step_handler(msg, process_vehicle_power_step, vehicle)

        def process_vehicle_power_step(message, vehicle):
            vehicle.power = message.text
            
            msg = self.bot.send_message(message.chat.id, 'Рік випуску')
            self.bot.register_next_step_handler(msg, process_vehicle_year_step, vehicle)

        def process_vehicle_year_step(message, vehicle):
            vehicle.manufacture_year = message.text
            
            self.bot.send_message(message.chat.id, 'Готово')

            self.default_message(message)

            self.vehicle_manager.add(vehicle)

        if message.text == '🚜 Облік техніки':
            markup = types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
            btn1 = types.KeyboardButton('🟢 Додати техніку')
            btn2 = types.KeyboardButton('🔴 Видалити техніку')
            btn3 = types.KeyboardButton('📝 Переглянути список техніки')
            btn4 = types.KeyboardButton('⬅️ Назад')
            markup.add(btn1, btn2, btn3, btn4)
            self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)    
            return True

        if message.text == '🟢 Додати техніку':
            markup = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
            btn1 = types.KeyboardButton('Зерновоз')
            btn2 = types.KeyboardButton('Самосвал')
            btn3 = types.KeyboardButton('Фургон')
            btn4 = types.KeyboardButton('Трактор')
            btn5 = types.KeyboardButton('Косарка')
            btn6 = types.KeyboardButton('Сівалка')
            btn7 = types.KeyboardButton('Комбайн')
            btn8 = types.KeyboardButton('Інша техніка')

            markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8)
            self.bot.send_message(message.chat.id, 'Виберіть тип', reply_markup=markup)
            
            self.bot.register_next_step_handler(message, process_vehicle_type_step)
            return True

        if message.text == '🔴 Видалити техніку':

            self.bot.send_message(message.chat.id, 'Введіть id:')

            self.bot.register_next_step_handler(message, proccess_vehicle_delete)
            return True

        if message.text == '📝 Переглянути список техніки':
            if not message.chat.id in self.user_dict:
                self.user_dict[message.chat.id] = 0

            vehicles = self.vehicle_manager.get_list()
            show_vehicles = []
            for i in range(0, 3):
                try:
                    show_vehicles.append(vehicles[i])
                except:
                    break
            
            if len(show_vehicles) == 0:
                self.bot.send_message(message.chat.id, 'В парку немає техніки')
                return True

            pages_count = str(math.trunc(vehicles.collection.count_documents({}) / 3 + 1))

            markup = types.InlineKeyboardMarkup()
            markup.row_width = 3
            markup.add(types.InlineKeyboardButton('<---', callback_data='cb_prev'),
                                    types.InlineKeyboardButton('--->', callback_data='cb_next'),
                                    types.InlineKeyboardButton('Назад', callback_data='cb_exit'))

            index = 0
            text = ''
            for vehicle in show_vehicles:
                text += '---------\n'
                text += 'id: ' + str(index) + '\n'
                
                text += 'Тип техніки: ' + vehicle['type'] + '\n'
                text += 'Марка: ' + vehicle['mark'] + '\n'
                text += 'Модель: ' + vehicle['model'] + '\n'
                text += 'Регістраційний номер: ' + vehicle['number'] + '\n'
                text += 'VIN код, номер шасі (кузова, рами): ' + vehicle['vin_code'] + '\n'
                text += 'Об’єм двигуна (л): ' + vehicle['engine_capacity'] + '\n'
                text += 'Потужність (к. с.): ' + vehicle['power'] + '\n'
                text += 'Рік випуску: ' + vehicle['manufacture_year'] + '\n'
                text += 'Одометр: ' + vehicle['odometr'] + ' км\n'
                text += 'Паливо: ' + str(vehicle['fuel']) + ' л\n'
                index += 1
            text += '---------\n'
            text += 'Сторінка 1/' + pages_count
            
            self.bot.send_message(message.chat.id, text, reply_markup=markup)
            return True

        return False 
        
    def calculator_dialog(self, message):
        def process_calc_type_1_step_1(message):
            wasted_fuel = message.text
            self.bot.send_message(message.chat.id, 'Введіть відстань яку ви проїхали (км)')
            self.bot.register_next_step_handler(message, process_calc_type_1_step_2, wasted_fuel)
        
        def process_calc_type_1_step_2(message, wasted_fuel):
            try:
                distance = int(message.text)
                wasted_fuel = int(wasted_fuel)
                result = Calculator.fuel_consumption(distance, wasted_fuel)
                self.bot.send_message(message.chat.id, f'{"{:.1f}".format(result)} л/км')
            except:
                self.bot.send_message(message.chat.id, f'Помикла, спробуйте ще раз')
            self.default_message(message)

        def process_calc_type_2_step_1(message):
            wasted_fuel = message.text
            self.bot.send_message(message.chat.id, 'Введіть вартість 1 л топлива (грн)')
            self.bot.register_next_step_handler(message, process_calc_type_2_step_2, wasted_fuel)

        def process_calc_type_2_step_2(message, wasted_fuel):
            fuel_cost = message.text
            self.bot.send_message(message.chat.id, 'Введіть відстань яку потрібно проїхати (км)')
            self.bot.register_next_step_handler(message, process_calc_type_2_step_3, wasted_fuel, fuel_cost)

        def process_calc_type_2_step_3(message, wasted_fuel, fuel_cost):
            try:
                distance = int(message.text)
                wasted_fuel = int(wasted_fuel)
                fuel_cost = int(fuel_cost)

                result = Calculator.fuel_cost(wasted_fuel, fuel_cost)

                self.bot.send_message(message.chat.id, f'Вартість 1 км: {"{:.1f}".format(result)} грн')
                self.bot.send_message(message.chat.id, f'Вартість {str(distance)} км: {"{:.1f}".format(result * distance)} грн')
            except:
                self.bot.send_message(message.chat.id, f'Помикла, спробуйте ще раз11')
            self.default_message(message)

        def process_calc_type_3_step_1(message):
            wasted_fuel = message.text
            self.bot.send_message(message.chat.id, 'Введіть потужність двигуна (к. с.)')
            self.bot.register_next_step_handler(message, process_calc_type_3_step_2, wasted_fuel)
        
        def process_calc_type_3_step_2(message, wasted_fuel):
            try:
                engine_power = int(message.text)
                wasted_fuel = int(wasted_fuel)
                result = Calculator.fuel_consumption_per_hour(wasted_fuel, engine_power)
                self.bot.send_message(message.chat.id, f'{"{:.1f}".format(result)} л/год')
            except:
                self.bot.send_message(message.chat.id, f'Помикла, спробуйте ще раз')
            self.default_message(message)


        if message.text == '🧮 Калькулятори':
            markup = types.ReplyKeyboardMarkup(row_width=1)
            btn1 = types.KeyboardButton('📝 Розрахунок розходу на 100 км')
            btn2 = types.KeyboardButton('📝 Розрахунок вартості палива на 1 км')
            btn3 = types.KeyboardButton('📝 Розрахунок розходу палива на годину роботи')
            btn4 = types.KeyboardButton('⬅️ Назад')
            markup.add(btn1, btn2, btn3, btn4)
            self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)
            return True

        if message.text == '📝 Розрахунок розходу на 100 км':
            self.bot.send_message(message.chat.id, 'Введіть витрачене паливо (л)')
            self.bot.register_next_step_handler(message, process_calc_type_1_step_1)
            return True

        if message.text == '📝 Розрахунок вартості палива на 1 км':
            self.bot.send_message(message.chat.id, 'Введіть розхід топлива на 100 км. (л/км)')
            self.bot.register_next_step_handler(message, process_calc_type_2_step_1)
            return True

        if message.text == '📝 Розрахунок розходу палива на годину роботи':
            self.bot.send_message(message.chat.id, 'Введіть питомий розхід палива (гкВт/год)')
            self.bot.register_next_step_handler(message, process_calc_type_3_step_1)
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
            
        def process_add_fuel_to_vehicle_step_1(message):
            vehicle_id = int(message.text)
            self.bot.send_message(message.chat.id, "Введіть кількість палива:")
            self.bot.register_next_step_handler(message, process_add_fuel_to_vehicle_step_2, vehicle_id)

        def process_add_fuel_to_vehicle_step_2(message, vehicle_id):
            fuel = int(message.text)
            self.fuel_manager.add_to_vehicle(vehicle_id, fuel)
            self.bot.send_message(message.chat.id, 'Готово')
            self.default_message(message)

        if message.text == '⛽ Облік залишків палива':
            markup = types.ReplyKeyboardMarkup(row_width=2)
            btn1 = types.KeyboardButton('🟢 Додати паливо до складу')
            btn2 = types.KeyboardButton('🚛 Додати паливо до техніки')
            btn3 = types.KeyboardButton('🔴 Видалити паливо зі складу')
            btn4 = types.KeyboardButton('📝 Перегляд залишків палива')
            btn5 = types.KeyboardButton('⬅️ Назад')
            markup.add(btn1, btn2, btn3, btn4, btn5)
            self.bot.send_message(message.chat.id, "Виберіть:", reply_markup=markup)
            return True

        if message.text == '🟢 Додати паливо до складу':
            self.bot.send_message(message.chat.id, "Введіть кількість палива:")
            self.bot.register_next_step_handler(message, process_add_fuel)
            return True
    
        if message.text == '🚛 Додати паливо до техніки':
            self.bot.send_message(message.chat.id, "Введіть id техніки:")
            self.bot.register_next_step_handler(message, process_add_fuel_to_vehicle_step_1)
            return True

        if message.text == '🔴 Видалити паливо зі складу':
            self.bot.send_message(message.chat.id, "Введіть кількість палива:")
            self.bot.register_next_step_handler(message, process_remove_fuel)
            return True

        if message.text == '📝 Перегляд залишків палива':
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
                if current_step <= self.vehicle_manager.get_list().collection.count_documents({}) - 3:
                    current_step += 3
                else:
                    return

            elif call.data == 'cb_exit':
                del self.user_dict[call.message.chat.id]
                self.default_message(call.message)
                
                # self.bot.delete_message(call.message.chat.id, call.message.message_id)
                
            self.user_dict[call.message.chat.id] = current_step

            vehicles = self.vehicle_manager.get_list()
            show_vehicles = []
            for i in range(current_step, current_step + 3):
                try:
                    show_vehicles.append(vehicles[i])
                except:
                    break

            current_page = str(math.trunc(current_step / 3 + 1))
            pages_count = str(math.trunc(vehicles.collection.count_documents({}) / 3 + 1))

            index = 0
            text = ''
            for vehicle in show_vehicles:
                text += '---------\n'
                text += 'id: ' + str(index + current_step) + '\n'
                
                text += 'Тип автомобіля: ' + vehicle['type'] + '\n'
                text += 'Марка: ' + vehicle['mark'] + '\n'
                text += 'Модель: ' + vehicle['model'] + '\n'
                text += 'Регістраційний номер: ' + vehicle['number'] + '\n'
                text += 'VIN код, номер шасі (кузова, рами): ' + vehicle['vin_code'] + '\n'
                text += 'Об’єм двигуна (л): ' + vehicle['engine_capacity'] + '\n'
                text += 'Потужність (к. с.): ' + vehicle['power'] + '\n'
                text += 'Рік випуску: ' + vehicle['manufacture_year'] + '\n'
                text += 'Одометр: ' + vehicle['odometr'] + ' км\n'
                text += 'Паливо: ' + str(vehicle['fuel']) + ' л\n'

                index += 1

            
            text += '---------\n'
            text += f'Сторінка {current_page}/{pages_count}'

            try:
                self.bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
            except:
                pass

        @self.bot.message_handler(func=lambda message: True)
        def handle_all_messages(message):
            if not self.vehicle_dialog(message):
                if not self.fuel_dialog(message):
                    if not self.calculator_dialog(message):
                        self.default_message(message)


def load_config():
    with open('config.json') as f:
        config = json.load(f)
    return config

def main():
    config = load_config()

    dialog = DialogManager(config)
    dialog.start()


if __name__ == "__main__":
    main()




