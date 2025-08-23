import app

def test_get_time_window():
    query = "how much did I spend in target last month?"
    #result = app.get_time_window(query)
    result = app.search_transactions(query)
    print(result)


def test_query_transactions():
    transactions = app.query_transactions('2024-12-01', '2025-06-21')
    print(transactions)

def test_get_insights():
    query = "how much did I spend in groceries for the last six months?"
    transactions = app.get_insights(query, app.query_transactions('2024-11-01', '2025-05-11'))
    print(transactions)

if __name__ == '__main__':
    #print(test_query_transactions())
    print(test_get_time_window())


