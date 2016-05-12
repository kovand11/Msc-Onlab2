from qpython import qconnection
import matplotlib.pyplot as plt
import numpy
import bisect
import time

def classify_trades(q,ex):
    #loading the quote index file, and transfering client side
    q.sync('ctx_table:flip `SYMBOL`TDATE`TBEGREC`TENDREC!("siii";10 4 4 4) 1: (`:/q/data/T200405A.IDX)')
    q.sync('cqx_table:flip `SYMBOL`QDATE`QBEGREC`QENDREC!("siii";10 4 4 4) 1: (`:/q/data/Q200405A.IDX)')
    symbol_index = q.sync('select SYMBOL,TBEG:TBEGREC,TEND:TENDREC,QBEG:QBEGREC,QEND:QENDREC from ctx_table ij (`SYMBOL xkey cqx_table)')

    plot_p = []
    plot_b = []
    plot_o = []

    for i in range(0,len(symbol_index)):
        t_rec_len = 29
        q_rec_len = 39
        symb = symbol_index[i][0]
        tbeg = symbol_index[i][1]
        tend = symbol_index[i][2]
        qbeg = symbol_index[i][3]
        qend = symbol_index[i][4]
        print("%d/%d procesing: %s" % (i, len(symbol_index), symb))
        #loading the tables server side
        q.sync('ctb_table:flip `TTIM`PRICE`SIZ`TSEQ`G127`CORR`COND`EX!("ijiihhsc";4 8 4 4 2 2 4 1) 1: (`:/q/data/T200405A.BIN,%s,%s)' % ((tbeg-1)*t_rec_len,(tend-tbeg)*t_rec_len))
        q.sync('ctq_table:flip `QTIM`BID`OFR`QSEQ`BIDSIZE`OFRSIZ`MODE`EX`MMID!("ijjiiihcs";4 8 8 4 4 4 2 1 4) 1: (`:/q/data/Q200405A.BIN,%s,%s)' % ((qbeg-1)*q_rec_len,(qend-qbeg)*q_rec_len))
        q.sync('t_sym_ex:`TTIM xasc select TTIM,PRICE from ctb_table where EX="%s"' % ex)
        q.sync('q_sym_ex:`QTIM xasc select QTIM,BID,OFR from ctq_table where EX="%s"' % ex)
        t_sym_ex = q.sync('flip t_sym_ex')
        q_sym_ex = q.sync('flip q_sym_ex')
        qtim = q_sym_ex[numpy.string_('QTIM')]
        if len(qtim) < 2:
            continue
        bid = q_sym_ex[numpy.string_('BID')]
        ofr = q_sym_ex[numpy.string_('OFR')]

        ttim = t_sym_ex[numpy.string_('TTIM')]
        price = t_sym_ex[numpy.string_('PRICE')]
        lbid = [None]*len(ttim)
        lofr = [None]*len(ttim)
        lee_ready_class = [None]*len(ttim)
        for j in range(0,len(ttim)):
            ind = bisect.bisect_left(qtim, ttim[j] - 5)  # best bid and ofr from 5 sec before
            lee_ready_class[j] = 'green'
            if ind != 0:
                lbid[j] = bid[ind-1]
                lofr[j] = ofr[ind-1]
                avg = (lbid[j] + lofr[j])/2
                if price[j] > avg:
                    lee_ready_class[j] = 'red'
                elif price[j] < avg:
                    lee_ready_class[j] = 'blue'
                else:
                    if price[j] > price[j-1]:
                        lee_ready_class[j] = 'red'
                    elif price[j] < price[j-1]:
                        lee_ready_class[j] = 'blue'

        if len(ttim)>5000000 and True:
            plt.suptitle(symb)
            plt.scatter(ttim,price,color = lee_ready_class)
            #plt.plot(ttim,price,'ro-',color = 'green')
            #plt.plot(ttim, lbid,color= 'blue')
            #plt.plot(ttim, lofr,color= 'red')
            plt.plot(qtim, bid, color='blue',linestyle='solid')
            plt.plot(qtim, ofr, color='red',linestyle='solid')

            spread = max(price) - min(price)
            avg = (max(price) + min(price))/2

            plt.axis([min(ttim), max(ttim), avg-0.6*spread, avg+0.6*spread])
            plt.show()
    return
	

if __name__ == '__main__':
    qcon = qconnection.QConnection(host='localhost', port=5000) #bme-host = f1.finance.bme.hu
    qcon.open()
    print(qcon)
    print('IPC version: %s. Is connected: %s' % (qcon.protocol_version, qcon.is_connected()))
    start_time = time.time()
    classify_trades(qcon,'A');
    elapsed = time.time() - start_time;
    print('classify_trades(qcon,\'A\') took: %d' % elapsed)
    qcon.close()
    plot_test()

#set