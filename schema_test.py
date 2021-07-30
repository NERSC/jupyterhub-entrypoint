import asyncio
from uuid import uuid4
from sqlalchemy import Column, ForeignKey, Table, Text, JSON
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import registry, relationship, selectinload, sessionmaker

get_type = type

mapper_registry = registry()
Base = mapper_registry.generate_base()


entrypoints_and_tags = Table(
    'entrypoints_and_tags',
    Base.metadata,
    Column('entrypoint_id', ForeignKey('entrypoints.id'), primary_key=True),
    Column('tag_id', ForeignKey('tags.id'), primary_key=True)
)

selections_and_tags = Table(
    'selections_association',
    Base.metadata,
    Column('selection_id', ForeignKey('selections.id'), primary_key=True),
    Column('tag_id', ForeignKey('tags.id'), primary_key=True)
)


class Entrypoint(Base):
    __tablename__ = "entrypoints"

    id = Column(Text, primary_key=True)
    user = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    data = Column(JSON)

    tags = relationship(
        "Tag",
        secondary=entrypoints_and_tags,
        back_populates="entrypoints"
    )

    def __repr__(self):
        return f'Entrypoint(name={self.name}, user={self.user}, type={self.type}, tags={self.tags})'


class Tag(Base):
    __tablename__ = "tags"

    id = Column("id", Text, primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)

    entrypoints = relationship(
        "Entrypoint",
        secondary=entrypoints_and_tags,
        back_populates="tags"
    )

    selections = relationship(
        "Selection",
        secondary=selections_and_tags,
        back_populates="tags"
    )

    def __repr__(self):
        return f'Tag(name={self.name})'


class Selection(Base):
    __tablename__ = "selections"

    id = Column(Text, primary_key=True)
    user = Column(Text, nullable=False)
    entrypoint_id = Column(Text, ForeignKey('entrypoints.id'), nullable=False)

    tags = relationship(
        "Tag",
        secondary=selections_and_tags,
        back_populates="selections"
    )

    def __repr__(self):
        return f'Selection(user={self.user}, entrypoint_id={self.entrypoint_id})'


# find any entrypoints that match the arguments
async def find_entrypoint(engine, id=-1, user='', name='', type='', tags=[]):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        async with session.begin():

            statement = select(Entrypoint).join(Entrypoint.tags).options(
                selectinload(Entrypoint.tags))

            if tags != []:
                statement = statement.filter(
                    Entrypoint.tags.any(Tag.name.in_(tags))
                )

            if id != -1:
                statement = statement.filter(Entrypoint.id == id)

            if user != '':
                statement = statement.filter(Entrypoint.user == user)

            if name != '':
                statement = statement.filter(Entrypoint.name == name)

            if type != '':
                statement = statement.filter(Entrypoint.type == type)

            res = await session.execute(statement.distinct())
            return [r.Entrypoint for r in res.all()]


# create a new entrypoint
async def create_entrypoint(engine, user='', name='', type='', data={}, tags=[]):
    if user == '' or name == '' or type == '':
        raise Exception('Error, non-nullable argument not set')

    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    
    async with async_session() as session:
        async with session.begin():
            entrypoint = Entrypoint(id=str(uuid4()), user=user, name=name, type=type, data=data, tags=tags)
            session.add(entrypoint)


# delete all entrypoints that match the arguments
async def delete_entrypoint(engine, id=-1, user='', name='', type='', tags=[]):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        async with session.begin():
            statement = Entrypoint.__table__.delete()

            if id != -1:
                statement = statement.where(Entrypoint.id == id)
            if user != '':
                statement = statement.where(Entrypoint.user == user)
            if name != '':
                statement = statement.where(Entrypoint.name == name)
            if type != '':
                statement = statement.where(Entrypoint.type == type)
            if tags != []:
                for tag in tags:
                    statement = statement.where(tag in Entrypoint.tags)

            return await session.execute(statement)


# change the current selected entrypoint for a user
async def update_selection(engine, entrypoint_id=-1, user=''):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        async with session.begin():
            session.add(Selection(id=str(uuid4()), user=user,
                        entrypoint_id=entrypoint_id))


# clear the current selected entrypoint for a user
async def clear_selection(engine, user=''):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        async with session.begin():
            statement = Selection.__table__.delete().where(Selection.user == user)
            return await session.execute(statement)


# get the current selected entrypoint for a user
async def get_selection(engine, user=''):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        async with session.begin():
            statement = select(Selection).filter(Selection.user == user)
            res = await session.execute(statement)

            res = res.all()
            if (len(res) == 0):
                return None
            return res[0].Selection


async def create_tag(engine, name):
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        async with session.begin():
            statement = select(Tag).filter(Tag.name == name)
            res = await session.execute(statement)

            res = res.all()
            if (len(res) == 0):
                return Tag(name=name, id=str(uuid4()))
            return res[0].Tag


async def main():
    # engine = create_async_engine("sqlite+aiosqlite:///memory")  # database.db")
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory", echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await create_entrypoint(engine, user='jgeden', name='conda1', type='conda', data={}, tags=[await create_tag(engine, 'cori')])
    await create_entrypoint(engine, user='jgeden', name='dask:latest', type='shifter', tags=[await create_tag(engine, 'cori'), await create_tag(engine, 'perlmutter')])
    await create_entrypoint(engine, user='rcthomas', name='conda1', type='conda', data={}, tags=[await create_tag(engine, 'cori')])
    await create_entrypoint(engine, user='rcthomas', name='script1', type='script', data={}, tags=[await create_tag(engine, 'cori')])
    await create_entrypoint(engine, user='rcthomas', name='conda2', type='conda', tags=[await create_tag(engine, 'perlmutter')])

    print('\nGetting *')
    res = await find_entrypoint(engine)
    for e in res:
        print('*', e)

    print('\nGetting user=jgeden, name=conda1')
    res = await find_entrypoint(engine, user='jgeden', name='conda1')
    for e in res:
        print('*', e)

    print('\nGetting tag=perlmutter')
    res = await find_entrypoint(engine, tags=['perlmutter'])
    for e in res:
        print('*', e)

    print('\nGetting name=conda1')
    res = await find_entrypoint(engine, name='conda1')
    for e in res:
        print('*', e)

    print()

    print('Removing name=conda1 for user=jgeden')
    await delete_entrypoint(engine, user='jgeden', name='conda1')

    print('Getting name=conda1')
    res = await find_entrypoint(engine, name='conda1')
    for e in res:
        print('*', e)

    print()

    res = await find_entrypoint(engine, user='rcthomas', name='conda1')
    res = res[0]
    await update_selection(engine, entrypoint_id=res.id, user='rcthomas')

    print('Get selection for rcthomas')
    res = await get_selection(engine, user='rcthomas')
    print('*', res)

    print('Clear selection for rcthomas')
    await clear_selection(engine, user='rcthomas')

    print('Get selection for rcthomas')
    res = await get_selection(engine, user='rcthomas')
    print('*', res)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
