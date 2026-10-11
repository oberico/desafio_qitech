from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

RESPONSE_FIELDS = {"method", "version", "fee_bps", "release_window_hours", "created_at"}


class TestPaymentMethodVersioning:
    def test_new_values_create_the_next_version(self, changed_method, payment_methods):
        _, current = changed_method("boleto", 1111, 11)

        status, response = payment_methods.put("boleto", 2222, 12)

        assert status == 201
        assert response["version"] == current["version"] + 1
        assert response["method"] == "boleto"
        assert response["fee_bps"] == 2222
        assert response["release_window_hours"] == 12

    def test_response_has_only_the_contract_fields(self, changed_method):
        _, response = changed_method("boleto", 1112, 11)
        assert set(response.keys()) == RESPONSE_FIELDS
        assert datetime.fromisoformat(response["created_at"]).tzinfo is not None

    def test_same_values_return_the_current_version_without_creating_another(self, changed_method, payment_methods):
        _, current = changed_method("boleto", 1113, 11)

        status, response = payment_methods.put("boleto", 1113, 11)

        assert status == 200
        assert response["version"] == current["version"]
        assert response["created_at"] == current["created_at"]

    def test_same_values_do_not_advance_the_version_for_the_next_change(self, changed_method, payment_methods):
        _, current = changed_method("boleto", 1114, 11)
        payment_methods.put("boleto", 1114, 11)

        _, next_version = payment_methods.put("boleto", 1115, 11)

        assert next_version["version"] == current["version"] + 1

    def test_changing_only_the_window_creates_a_version(self, changed_method, payment_methods):
        _, current = changed_method("boleto", 1116, 11)

        status, response = payment_methods.put("boleto", 1116, 12)

        assert status == 201
        assert response["version"] == current["version"] + 1

    def test_versions_are_independent_per_method(self, changed_method, payment_methods):
        _, boleto = changed_method("boleto", 1117, 11)
        _, card = changed_method("card", 1117, 11)

        _, boleto_next = payment_methods.put("boleto", 1118, 11)

        assert boleto_next["version"] == boleto["version"] + 1
        _, card_same = payment_methods.put("card", 1117, 11)
        assert card_same["version"] == card["version"]

    def test_concurrent_identical_changes_create_exactly_one_version(self, changed_method, payment_methods):
        _, current = changed_method("card", 1119, 11)

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: payment_methods.put("card", 3333, 13), range(10)))

        statuses = sorted(status for status, _ in results)
        assert statuses == [200] * 9 + [201]
        assert {response["version"] for _, response in results} == {current["version"] + 1}
