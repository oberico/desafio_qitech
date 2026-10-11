from models import Client


class AuthIdentityDTO:
    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        return {
            "client_key": client.client_key,
            "companies": [
                {
                    "company_key": company.company_key,
                    "account_key": company.account.account_key if company.account else None,
                    "account_status": company.account.status.enumerator if company.account else None,
                }
                for company in client.companies
            ],
        }
