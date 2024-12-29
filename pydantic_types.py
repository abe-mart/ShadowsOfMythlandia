from pydantic import BaseModel
from typing import List

# Dungeon Rooms

class RoomDetails(BaseModel):
    id: int
    name: str
    description: str

class DungeonRoomInfo(BaseModel):
    current_room: RoomDetails
    neighbors: List[RoomDetails]

# Monsters

class MonsterInfo(BaseModel):
    id: int
    name: str
    description: str
    room_id: int
    hp: int
    attack: int

class MonstersInfo(BaseModel):
    monsters: List[MonsterInfo]

# Items

class ItemInfo(BaseModel):
        name: str
        description: str
        is_sword: bool

class ItemsInfo(BaseModel):
    items: List[ItemInfo]