from models import Company


class CompanyDTO:
    @staticmethod
    def obj_to_dict(company: Company) -> dict:
        account = company.account
        return {
            "company_key": company.company_key,
            "cnpj": company.cnpj,
            "legal_name": company.legal_name,
            "account_key": account.account_key if account else None,
            "account_status": account.status.enumerator if account else None,
        }
