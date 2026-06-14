from apps.bot.services.parser import parse_command


class TestParser:

    def test_sale_parsing(self):
        result = parse_command("non 10 dona sotdim")
        assert result['action'] == 'sale'
        assert result['product'] == 'non'
        assert result['quantity'] == 10

    def test_restock_parsing(self):
        result = parse_command("5 qop un keldi")
        assert result['action'] == 'restock'
        assert result['product'] == 'un'
        assert result['quantity'] == 5

    def test_debt_parsing(self):
        result = parse_command("sardor 50000 qarzga")
        assert result['action'] == 'debt'
        assert result['customer'] == 'sardor'
        assert result['amount'] == 50000

    def test_report_parsing(self):
        result = parse_command("bugungi statistika")
        assert result['action'] == 'report'

    def test_unknown_returns_none(self):
        result = parse_command("salom qalaysan")
        assert result is None