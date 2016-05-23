from qpython import qconnection
import numpy
import bisect
import time

#symbolwise only works if symbol_filter has entries
def process_range(q,path,beg,end,ex,symbol_filter,daywise,symbolwise):
    dates_table = q.sync('`TDATE`CQIDXB`CQIDXE`CTIDXB`CTIDXE`DISK`DATAFMT!("SSSSS S S";8 8 8 8 8 1 1 1 1) 0: (`:/storage/share/egyeb/DATE2_B.DAT)')

    dates = dates_table[numpy.string_('TDATE')]
    qb = dates_table[numpy.string_('CQIDXB')]
    qe = dates_table[numpy.string_('CQIDXE')]
    tb = dates_table[numpy.string_('CTIDXB')]
    te = dates_table[numpy.string_('CTIDXE')]
    disk = dates_table[numpy.string_('DISK')]
    fmt = dates_table[numpy.string_('DATAFMT')]

    if symbolwise:
        filemap = dict.fromkeys(symbol_filter)
        for s in filemap.keys():
            s_str = str(s)
            s_str = s_str[2:len(s_str) - 1]
            print(s_str)
            filemap[s] = open(str(s_str + '.csv'), 'w')

    for i in range(len(dates)):
        if beg <= dates[i] < end:
            #open the tind qind partially
            dateletter = str(dates[i])[2:8] + str(disk[i])[2]
            tibeg = int(tb[i])
            tiend = int(te[i])
            qibeg = int(qb[i])
            qiend = int(qe[i])
            index_len = 22;


            #load the trade index file
            q.sync('ctx_table:flip `SYMBOL`TDATE`TBEGREC`TENDREC!("siii";10 4 4 4) 1: (`:%sT%s.IDX,%d,%d)' % (path,dateletter,(tibeg-1)*index_len,(tiend-tibeg)*index_len))
            #load the quote index file
            q.sync('cqx_table:flip `SYMBOL`QDATE`QBEGREC`QENDREC!("siii";10 4 4 4) 1: (`:%sQ%s.IDX,%d,%d)' % (path,dateletter,(qibeg-1)*index_len,(qiend-qibeg)*index_len))
            #load the begin and end position of of the symbols in the binary files
            symbol_index = q.sync('select SYMBOL,TBEG:TBEGREC,TEND:TENDREC,QBEG:QBEGREC,QEND:QENDREC from ctx_table ij (`SYMBOL xkey cqx_table)')
            date_str = str(dates[i])
            date_str = date_str[2:len(date_str)-1]

            if daywise:
                csvfile = open(str(date_str+'.csv'), 'w')




            #for each symbol (possible filtering later)
            for j in range(0, len(symbol_index)):
                symb = symbol_index[j][0]
                if symb in symbol_filter or len(symbol_filter)==0:
                    t_rec_len_2 = 29
                    q_rec_len_2 = 39
                    t_rec_len_3 = 19
                    q_rec_len_3 = 27
                    tbeg = symbol_index[j][1]
                    tend = symbol_index[j][2]
                    qbeg = symbol_index[j][3]
                    qend = symbol_index[j][4]
                    print("%s: %d/%d procesing: %s" % (date_str,j, len(symbol_index), symb))
                    # loading corresponding part of the binary files server side
                    if fmt[i] == numpy.string_('2'):
                        q.sync(
                            'ctb_table:flip `TTIM`PRICE`SIZ`TSEQ`G127`CORR`COND`EX!("ijiihhsc";4 8 4 4 2 2 4 1) 1: (`:%sT%s.BIN,%s,%s)' % (
                                path, dateletter, (tbeg - 1) * t_rec_len_2, (tend - tbeg) * t_rec_len_2))
                        q.sync(
                            'ctq_table:flip `QTIM`BID`OFR`QSEQ`BIDSIZE`OFRSIZ`MODE`EX`MMID!("ijjiiihcs";4 8 8 4 4 4 2 1 4) 1: (`:%sQ%s.BIN,%s,%s)' % (
                                path, dateletter, (qbeg - 1) * q_rec_len_2, (qend - qbeg) * q_rec_len_2))
                        #load the relevant data from a specific exchange
                    elif fmt[i] == numpy.string_('3'):
                        q.sync(
                            'ctb_table:flip `TTIM`PRICE`SIZ`G127`CORR`COND`EX!("iiihhsc";4 4 4 2 2 2 1) 1: (`:%sT%s.BIN,%s,%s)' % (
                                path, dateletter, (tbeg - 1) * t_rec_len_3, (tend - tbeg) * t_rec_len_3))
                        q.sync(
                            'ctq_table:flip `QTIM`BID`OFR`BIDSIZE`OFRSIZ`MODE`EX`MMID!("iiiiihcs";4 4 4 4 4 2 1 4) 1: (`:%sQ%s.BIN,%s,%s)' % (
                                path, dateletter, (qbeg - 1) * q_rec_len_3, (qend - qbeg) * q_rec_len_3))
                    else:
                        print ('ERROR: unknown format: %s' % fmt[i])
                        continue

                    q.sync('t_sym_ex:`TTIM xasc select TTIM,PRICE from ctb_table where EX="%s"' % ex)
                    q.sync('q_sym_ex:`QTIM xasc select QTIM,BID,OFR from ctq_table where EX="%s"' % ex)
                    t_sym_ex = q.sync('flip t_sym_ex')
                    q_sym_ex = q.sync('flip q_sym_ex')
                    qtim = q_sym_ex[numpy.string_('QTIM')]
                    if len(qtim) < 2:
                        print('ERROR: No sufficient amount of quotes')
                        continue
                    bid = q_sym_ex[numpy.string_('BID')]
                    ofr = q_sym_ex[numpy.string_('OFR')]

                    ttim = t_sym_ex[numpy.string_('TTIM')]
                    price = t_sym_ex[numpy.string_('PRICE')]
                    lbid = [None] * len(ttim)
                    lofr = [None] * len(ttim)
                    lee_ready_class = [None] * len(ttim)
                    #Lee-Ready classification
                    for k in range(0, len(ttim)):
                        ind = bisect.bisect_left(qtim, ttim[k] - 5)  # best bid and ofr from 5 sec before
                        lee_ready_class[k] = 0
                        if ind != 0:
                            lbid[k] = bid[ind - 1]
                            lofr[k] = ofr[ind - 1]
                            avg = (lbid[k] + lofr[k]) / 2
                            if price[k] > avg:
                                lee_ready_class[k] = 1
                            elif price[k] < avg:
                                lee_ready_class[k] = -1
                            else:
                                for l in  range(1,k):
                                    if price[k] > price[k - l]:
                                        lee_ready_class[k] = 1
                                        break
                                    elif price[k] < price[k - l]:
                                        lee_ready_class[k] = -1
                                        break
                    #generating output an output line: symbol,buy,sell,unclassified
                    out_sym = str(symb)
                    out_sym = out_sym[2:len(out_sym)-1]
                    out_sell = str(lee_ready_class.count(-1));
                    out_buy = str(lee_ready_class.count(1));
                    out_unclass = str(lee_ready_class.count(0));

                    if daywise:
                        csvfile.write(out_sym+','+out_buy+','+out_sell+','+out_unclass+'\n')



                    print(out_buy)
                    if symbolwise:
                        filemap[symb].write(date_str+','+out_buy+','+out_sell+','+out_unclass+'\n')

            if daywise:
                csvfile.close()

    if symbolwise:
        for s in filemap.keys():
            filemap[s].close()

    return

if __name__ == '__main__':
    qcon = qconnection.QConnection(host='f1.finance.bme.hu', port=5001) #bme-host = f1.finance.bme.hu
    qcon.open()
    print(qcon)
    print('IPC version: %s. Is connected: %s' % (qcon.protocol_version, qcon.is_connected()))
    start_time = time.time()
    symbol_filter = []
    #symbol_filter.append(numpy.string_('XOM'))
    #symbol_filter.append(numpy.string_('WMT'))
    #symbol_filter.append(numpy.string_('IBM'))
    #symbol_filter.append(numpy.string_('JNJ'))
    #symbol_filter.append(numpy.string_('PFE'))
    symbol_filter.append(numpy.string_('AAPL'))
    process_range(qcon,'/storage/share/',numpy.string_('20040501'),numpy.string_('20040505'),'A',symbol_filter,daywise = False,symbolwise = True)
    elapsed = time.time() - start_time;
    print('classify_trades(qcon,\'A\') took: %d' % elapsed)
    qcon.close()