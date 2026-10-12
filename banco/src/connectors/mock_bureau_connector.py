REJECTED_CNPJ_SUFFIX = "-00"
REJECTION_REASON = "reprovada no birô"


class MockBureauConnector:
    def approves(self, cnpj: str) -> bool:
        return not cnpj.endswith(REJECTED_CNPJ_SUFFIX)
