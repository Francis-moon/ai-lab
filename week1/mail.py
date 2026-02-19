import random


class Slot:
    STATES = ('free', 'occupied', 'reserved', 'error')

    def __init__(self, slot_id, state=None):
        self.slot_id = slot_id
        self.state = state


class SlotManager:
    def __init__(self):
        self.slots = []

    def create_random_slots(self, n=10):
        self.slots = [Slot(slot_id=i + 1) for i in range(n)]
        return self.slots

    def print_statuses(self):
        for s in self.slots:
            print(s.status())


# def main():
    # mgr = SlotManager()
    # mgr.create_random_slots(10)
    # mgr.print_statuses()


if __name__ == '__main__':
    slot001 = Slot(slot_id=1, state='free')
    slot002 = Slot(slot_id=2, state='occupied')
    slot003 = Slot(slot_id=3, state='reserved')
    slot004 = Slot(slot_id=4, state='error') 
    slot005 = Slot(slot_id=5, state='free')
    slot006 = Slot(slot_id=6, state='occupied')
    slot007 = Slot(slot_id=7, state='reserved')
    slot008 = Slot(slot_id=8, state='error')  
    slot009 = Slot(slot_id=9, state='free')
    slot010 = Slot(slot_id=10, state='occupied')
    print(slot001.state)
    print(slot002.state)
    print(slot003.state)
    print(slot004.state)