import app

def test_get_time_window():
    query = "how much did I spend in target last month?"
    result = app.get_time_window(query)
    print(result)


def test_query_transactions():
    transactions = app.query_transactions('2024-12-01', '2025-06-21')
    print(transactions)


if __name__ == '__main__':
    print(test_query_transactions())


