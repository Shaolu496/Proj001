from flask import Flask, render_template,request,g,redirect
import sqlite3,math,requests
import matplotlib.pylab as plt
import matplotlib
import os
import db_setting as dbf
matplotlib.use('agg')


app = Flask(__name__)
database = 'datafile.db'



def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect(database)
    return g.sqlite_db

@app.teardown_appcontext
def close_connection(exception):
    print("We closing sql connection now~~~")
    if hasattr(g,'sqlite_db'):
        g.sqlite_db.close()

@app.route('/')
def home():
    #data
    conn = get_db()
    cursor = conn.cursor()
    result = cursor.execute("select * from cash")
    cash_result = result.fetchall()

    #conclute TWD USD TOTAL
    twd = 0
    usd = 0
    for data in cash_result:
        twd += data[1]
        usd += data[2]
    #get rate    
    r=requests.get('https://tw.rter.info/capi.php')
    currency=r.json()['USDTWD']['Exrate']
    total = math.floor(twd + usd*currency)

    #get stock info
    result2 = cursor.execute("select * from stock")
    stock_result = result2.fetchall()
    unique_stock_list = []
    for data in stock_result:
        if data[1] not in unique_stock_list:
            unique_stock_list.append(data[1])
    
    #canclute stock value
    total_stock_value = 0


    stock_info = []
    for stock in unique_stock_list:
        result = cursor.execute("select * from stock where stock_id=?",(stock,))
        result = result.fetchall()
        stock_cost = 0 #cost
        shares = 0 #股數
        for d in result:
            shares += d[2]
            stock_cost += d[2] * d[3] + d[4] + d[5]
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo=" + stock
        response = requests.get(url)
        data = response.json()

        
        price_array = data['data']
 
        current_price = float(price_array[len(price_array)-1][6])

    #     #單一總市值
        total_vlaue = round(current_price * shares)
        total_stock_value += total_vlaue 
    #     #單一股票平均成本
        avg_cost = round(stock_cost / shares ,2)
    #     #單一股票報酬率
        rate_of_return = round((total_vlaue-stock_cost) * 100 / stock_cost,2)

        stock_info.append({'stock_id':stock,'stock_cost':stock_cost,'total_value':total_vlaue,
                           'average_cost':avg_cost,'shares':shares,'current_price':current_price,
                           'rate_of_return':rate_of_return
                           })

    for stock in stock_info:
        stock['value_percentage'] = round(stock['total_value'] * 100 / total_stock_value , 2)    

    #plot stock chart
    if len(unique_stock_list) != 0:
        labels = tuple(unique_stock_list)
        sizes = [d['total_value'] for d in stock_info]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes,labels=labels,autopct=None,shadow=None)
        fig.subplots_adjust(top=1,bottom=0,right=1,left=0,hspace=1,wspace=1)  
        plt.savefig("static/piechart.jpg",dpi=220)
    else:
        try:
            os.remove('static/piechart.jpg')
        except:
            pass

    if usd != 0 or twd != 0 or total_stock_value != 0:
        labels = ('USD','TWD','Stock')
        sizes = (usd * currency ,twd, total_stock_value) 
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes,labels=labels,autopct=None,shadow=None)
        fig.subplots_adjust(top=1,bottom=0,right=1,left=0,hspace=1,wspace=1)  
        plt.savefig("static/piechart2.jpg",dpi=220)
    else:
        try:
            os.remove('static/piechart2.jpg')
        except:
            pass

    data = {'show_pic1':os.path.exists('static/piechart.jpg'),'show_pic2':os.path.exists('static/piechart2.jpg')
        ,'total':total,'currency':currency,'usd':usd,'twd':twd,'cash_result':cash_result,'stock_info':stock_info}
    return render_template('index.html',data=data)

@app.route('/cash')
def cash_form():
    return render_template('cash.html')

@app.route('/cash', methods=['POST'])
def submit_cash():
    
    taiwanese_dollars = 0
    us_dollars = 0
    if request.values['taiwanese-dollars'] != "":
        taiwanese_dollars = request.values['taiwanese-dollars']
    if request.values['us-dollars'] != "":
        us_dollars = request.values['us-dollars']
    note = request.values['note']
    date = request.values['date']

    #update database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""insert into cash (taiwanese_dollars, us_dollars, note, date_info ) values (?, ?, ?, ?) """
                   ,(taiwanese_dollars,us_dollars,note,date))
    conn.commit()

    return redirect('/')

@app.route('/cash-delete',methods=['POST'])
def cash_delete():
    transaction_id = request.values['id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""delete from cash where  transaction_id=?""",(transaction_id))
    conn.commit()
    return redirect("/")

@app.route('/stock')
def stock_form():
    return render_template('stock.html')

@app.route('/stock', methods=['POST'])
def submit_stock():
    stock_id = request.values['stock-id']
    stock_num = request.values['stock-num']
    stock_price = request.values['stock-price']
    fee = 0
    tax = 0
    if request.values['processing-fee'] != '':
        fee = request.values['processing-fee']
    if request.values['tax'] != '':
        fee = request.values['tax']   
    date = request.values['date']

    #update database
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""insert into stock (stock_id, stock_num, stock_price, processing_fee, tax, date_info) values (?, ?, ?, ?, ?, ?) """
                   ,(stock_id,stock_num,stock_price,fee,tax,date))
    conn.commit()
    
    return redirect('/')

@app.route('/stock-delete',methods=['POST'])
def stock_delete():
    stock_id = request.values['sid']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""delete from stock where stock_id=?""",(stock_id,))
    conn.commit()
    return redirect("/")

if __name__ == '__main__':
    dbf.dbfile()
    app.run(debug=True)