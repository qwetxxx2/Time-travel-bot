from aiogram.fsm.state import State, StatesGroup


class TravelStates(StatesGroup):
    choosing_epoch = State()


class QuizStates(StatesGroup):
    answering = State()