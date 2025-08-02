from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base:
    id: any
    __name__: str

    # テーブル名を自動で生成（クラス名を小文字変換）
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
