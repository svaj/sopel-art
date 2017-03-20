from sqlalchemy import Column, DateTime, Integer, String, Text
from artbutt import Base

class Art(Base):
    __tablename__ = 'art'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    creator = Column(String(250), nullable=False)
    art = Column(Text, nullable=False)
    kinskode = Column(Text, nullable=False)
    irccode = Column(Text, nullable=False)
    display_count = Column(Integer, nullable=False)

