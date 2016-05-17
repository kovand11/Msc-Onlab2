from qpython import qconnection
import matplotlib.pyplot as plt
import numpy
import bisect
import time
import csv


#output 20050125.csv minden symb buys sells
def process_range(q,path,beg,end,ex):
    dates_table = q.sync('`TDATE`CQIDXB`CQIDXE`CTIDXB`CTIDXE`DISK`DATAFMT!("SSSSS S S";8 8 8 8 8 1 1 1 1) 0: (`:/storage/share/egyeb/DATE2_B.DAT)')

    dates = dates_table[numpy.string_('TDATE')]
    qb = dates_table[numpy.string_('CQIDXB')]
    qe = dates_table[numpy.string_('CQIDXE')]
    tb = dates_table[numpy.string_('CTIDXB')]
    te = dates_table[numpy.string_('CTIDXE')]
    disk = dates_table[numpy.string_('DISK')]
    fmt = dates_table[numpy.string_('DATAFMT')]

    for i in range(len(dates)):
        if beg <= dates[i] < end:
            #open the tind qind partially
            date = dates[i]#dbg
            dateletter = str(dates[i])[2:8] + str(disk[i])[2]
            tibeg = int(tb[i])
            tiend = int(te[i])
            qibeg = int(qb[i])
            qiend = int(qe[i])
            index_len = 22;
            q.sync('ctx_table:flip `SYMBOL`TDATE`TBEGREC`TENDREC!("siii";10 4 4 4) 1: (`:%sT%s.IDX,%d,%d)' % (path,dateletter,(tibeg-1)*index_len,(tiend-tibeg)*index_len))
            q.sync('cqx_table:flip `SYMBOL`QDATE`QBEGREC`QENDREC!("siii";10 4 4 4) 1: (`:%sQ%s.IDX,%d,%d)' % (path,dateletter,(qibeg-1)*index_len,(qiend-qibeg)*index_len))
            symbol_index = q.sync('select SYMBOL,TBEG:TBEGREC,TEND:TENDREC,QBEG:QBEGREC,QEND:QENDREC from ctx_table ij (`SYMBOL xkey cqx_table)')
            date_str = str(dates[i])
            date_str = date_str[2:len(date_str)-1]
            csvfile = open(str(date_str+'.csv'), 'w')
            for i in range(0, len(symbol_index)):
                t_rec_len = 29
                q_rec_len = 39
                symb = symbol_index[i][0]
                tbeg = symbol_index[i][1]
                tend = symbol_index[i][2]
                qbeg = symbol_index[i][3]
                qend = symbol_index[i][4]
                print("%s: %d/%d procesing: %s" % (date_str,i, len(symbol_index), symb))
                # loading the tables server side
                if symb == numpy.string_('PDCO'):
                    print('ctb_table:flip `TTIM`PRICE`SIZ`TSEQ`G127`CORR`COND`EX!("ijiihhsc";4 8 4 4 2 2 4 1) 1: (`:%sT%s.BIN,%s,%s)' % (
                    path,dateletter,(tbeg - 1) * t_rec_len, (tend - tbeg) * t_rec_len))
                q.sync(
                    'ctb_table:flip `TTIM`PRICE`SIZ`TSEQ`G127`CORR`COND`EX!("ijiihhsc";4 8 4 4 2 2 4 1) 1: (`:%sT%s.BIN,%s,%s)' % (
                    path,dateletter,(tbeg - 1) * t_rec_len, (tend - tbeg) * t_rec_len))
                q.sync(
                    'ctq_table:flip `QTIM`BID`OFR`QSEQ`BIDSIZE`OFRSIZ`MODE`EX`MMID!("ijjiiihcs";4 8 8 4 4 4 2 1 4) 1: (`:%sQ%s.BIN,%s,%s)' % (
                    path,dateletter,(qbeg - 1) * q_rec_len, (qend - qbeg) * q_rec_len))
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
                lbid = [None] * len(ttim)
                lofr = [None] * len(ttim)
                lee_ready_class = [None] * len(ttim)
                for j in range(0, len(ttim)):
                    ind = bisect.bisect_left(qtim, ttim[j] - 5)  # best bid and ofr from 5 sec before
                    lee_ready_class[j] = 0
                    if ind != 0:
                        lbid[j] = bid[ind - 1]
                        lofr[j] = ofr[ind - 1]
                        avg = (lbid[j] + lofr[j]) / 2
                        if price[j] > avg:
                            lee_ready_class[j] = 1
                        elif price[j] < avg:
                            lee_ready_class[j] = -1
                        else:
                            for k in  range(1,j):
                                if price[j] > price[j - k]:
                                    lee_ready_class[j] = 1
                                elif price[j] < price[j - k]:
                                    lee_ready_class[j] = -1
                #output
                out_sym = str(symb)
                out_sym = out_sym[2:len(out_sym)-1]
                out_sell = str(lee_ready_class.count(-1));
                out_buy = str(lee_ready_class.count(1));
                out_unclass = str(lee_ready_class.count(0));
                csvfile.write(out_sym+','+out_buy+','+out_sell+','+out_unclass+'\n')
            csvfile.close()

    return

if __name__ == '__main__':
    qcon = qconnection.QConnection(host='f1.finance.bme.hu', port=5001) #bme-host = f1.finance.bme.hu
    qcon.open()
    print(qcon)
    print('IPC version: %s. Is connected: %s' % (qcon.protocol_version, qcon.is_connected()))
    start_time = time.time()
    process_range(qcon,'/storage/share/',numpy.string_('20040501'),numpy.string_('20040601'),'A')
    elapsed = time.time() - start_time;
    print('classify_trades(qcon,\'A\') took: %d' % elapsed)
    qcon.close()

#set