from qpython import qconnection
import matplotlib.pyplot as plt
import numpy
import sys




def plot_trades(q, symb):
    # getting the trade data
    q.sync('ctx_table:flip`SYMBOL`TDATE`BEGREC`ENDREC!("siii";10 4 4 4) 1: (`:/q/data/T200405A.IDX)') # read the trade index
    symbol_start_end = q.sync('select BEGREC,ENDREC from ctx_table where SYMBOL=`%s' % symb) # get the corresponding indexes
    start = symbol_start_end[0][0]
    end = symbol_start_end[0][1]
    q.sync(
        'ctb_table:flip `TTIM`PRICE`SIZ`TSEQ`G127`CORR`COND`EX!("ijiihhsc";4 8 4 4 2 2 4 1) 1: (`:/q/data/T200405A.BIN,%s,%s)' % (
            29*(start - 1) , 29 * (end - start))) # all trades for the symbol
    trades = q.sync('flip `TTIM xasc select TTIM,PRICE,SIZ from ctb_table')
    x = trades[numpy.string_('TTIM')]
    x_hour = [it/(60*60) for it in x]
    y = trades[numpy.string_('PRICE')]
    y_usd = [it/10000000 for it in y]
    # getting the full name
    q.sync('mas_table:flip `SYMBOL`NAME`CUSIP`Ext`ITS`ICODE`SHARESOUT`UOT`DENOM`TYPE`DATEF!'
           '("SSSSSSSSSSS ";10 30 12 10 1 4 10 4 1 1 8 2) 0: (`:/q/data/M200405.TAB)')
    full_name = q.sync('select NAME from mas_table where SYMBOL=`%s' % symb)[0][0];
    plt.suptitle(str(full_name))
    plt.plot(x_hour, y_usd)
    plt.axis([min(x_hour), max(x_hour), min(y_usd), max(y_usd)])
    plt.show()
    return



if __name__ == '__main__':
    qcon = qconnection.QConnection(host='localhost', port=5000)
    qcon.open()
    symbol = sys.argv[1]
    plot_trades(qcon,symbol)
    qcon.close()
