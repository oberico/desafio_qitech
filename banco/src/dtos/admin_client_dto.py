from models import Client


class AdminClientDTO:
    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        return {
            "client_key": client.client_key,
            "name": client.name,
            "created_at": client.created_at.isoformat(),
        }
