from models import Client


class ClientDTO:
    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        return {
            "client_key": client.client_key,
            "cpf": client.cpf,
            "name": client.name,
            "birthdate": client.birthdate.isoformat(),
            "email": client.email,
        }
