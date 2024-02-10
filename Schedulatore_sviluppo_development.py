import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly_express as px
from datetime import time, timedelta, datetime, date
import math
from random import*
import geopy.distance

st.set_page_config(page_title="Planner interventi", layout='wide')


# Versione  v3 del 08-01-2024
# what's new:
# > interventi indivisibili


# Impostazione percorsi flat files

path_clara = '/Users/Alessandro/Documents/AB/Clienti/AB/Exera/Programmazione/Dicemebre/Clara_allowed.xlsx'
ordine_siti = pd.read_excel('/Users/Alessandro/Documents/AB/Clienti/AB/Exera/Programmazione/Siti_territoriali.xlsx')
siti=pd.read_excel('/Users/Alessandro/Documents/AB/Clienti/AB/Exera/cantieri.xls')
siti = siti[['id sito','lat','lng']]

anno_corrente = 2024
oggi = datetime.now().date()
deltas = {30:10,15:2,10:2,7:1,7.5:1,6:1}
viaggi = dict(zip(ordine_siti.SitoTerritoriale, ordine_siti.ViaggioAR))

def calendario_no_domeniche (mese, anno, operatore): #in realtà non ci sono neanche i sabati
    calendario = []
    inizio = date(anno, mese, 1) 
    calendario = [inizio]
    if mese in [11,4,6,9]:
        for i in range (29):#29
            calendario.append(inizio+timedelta(days=i+1))
    elif mese == 2:
        for i in range (30):#27 metto 30 
            calendario.append(inizio+timedelta(days=i+1))
    else:
        for i in range (30):#30
            calendario.append(inizio+timedelta(days=i+1))
            
    cal=pd.DataFrame(calendario).rename(columns={0:'Data'})
    cal['day']=[ data.weekday() for data in cal.Data]
    cal['day_n']=[ data.day for data in cal.Data]

    for i in range(len(cal)):
        if cal.Data.iloc[i].month != mese_n:
            cal['day_n'].iloc[i]=cal['day_n'].iloc[i-1]
            cal['Data'].iloc[i]=cal['Data'].iloc[i-1]

            
  

    cal = cal[(cal.day != 6) & (cal.day != 5)]
    cal['operatore']=operatore
    cal = cal.reset_index(drop=True)
            
    return cal


col_a, col_b = st.columns([4,1])
with col_a:
    st.title('Schedulatore interventi')
    
with col_b:
    st.image('/Users/Alessandro/Documents/AB/Clienti/AB/Exera/exera_logo.png')

st.subheader('',divider='grey')

# Caricamento file estratto da Byron

percorso = st.sidebar.file_uploader(f"Caricare l' elenco interventi estratto da Byron")
while percorso is None:
    st.stop()

df_raw=pd.read_excel(percorso)

# pulizia dati nan
df_raw.Sito = df_raw.Sito.astype(str).replace({'nan':'non disponibile'})
df_raw['Indirizzo Sito'] = df_raw['Indirizzo Sito'].astype(str).replace({'nan':'non disponibile'})
df_raw = df_raw.merge(siti,how='left',left_on='IdSito',right_on='id sito')

#rimozione voci fatturazione
fattura = ['FATTURAZIONE','fatturazione','Fatturazione']
df_raw = df_raw[[all(voce not in check for voce in fattura) for check in df_raw['IstruzioniOperative'].astype(str)]]
#rimozione ferrara tua
df_raw = df_raw[df_raw.Cliente != 'FERRARA TUA SPA']

#selected = ['FERRARA ','PMI 1','PMI 2']
#df_raw = df_raw[[(any(elemento in check for elemento in selected)) for check in df_raw.SitoTerritoriale.astype(str)]]

#creazione delle chiavi
df_raw['key'] = df_raw.Cliente + df_raw.Sito + " | " + df_raw['Indirizzo Sito'] + df_raw.Servizio
df_raw['key_sito'] =  df_raw.Cliente + df_raw.Sito + " | " + df_raw['Indirizzo Sito']
df_raw['key_univoca'] = df_raw.Cliente + df_raw.Sito + " | " + df_raw['Indirizzo Sito'] + df_raw.Servizio + df_raw.Periodicita

# Suddivisione  dei dataframe in: 
# Chiuso
# Pianificato
# Pianificabile

filtro_pianificati = [' ANTILARVALE 1',' SQUADRA 2',' SQUADRA 1',' SQUADRA 4',' SQUADRA 3',' SQUADRA 6',' 2 OPERATORI', ' VINCOLO ,' ,' SQUADRA 5' ]

# creo un dataframe di un mese (mese di pianificazione)

mesi = {1:'Gennaio', 2:'Febbraio',3:'Marzo',4:'Aprile',5:'Maggio',6:'Giugno',7:'Luglio',8:'Agosto',9:'Settembre',10:'Ottobre',11:'Novembre', 12:'Dicembre'}
key_list = list(mesi.keys())
val_list = list(mesi.values())
lista_unica = list(set([ data.month for data in df_raw['Data Inizio']]))
selezione = [ mesi[key] for key in lista_unica ]
mese_scelto = st.multiselect('Selezionare mese da pianificare', selezione)

while mese_scelto == []:
    st.stop()

valore = [key_list[val_list.index(n)] for n in mese_scelto ]
mese = df_raw[[ data.month in valore for data in df_raw['Data Inizio']]]
mese_n = min(valore)

# Calcolo della prima data pianificabile

calendario_pianificazione = calendario_no_domeniche(mese_n,anno_corrente,'standard')
st.write(calendario_pianificazione.Data.iloc[-1])
oggi_day = oggi.day+2#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
index_oggi = calendario_pianificazione[calendario_pianificazione.day_n==oggi_day].day_n.index[0]

next_working = calendario_pianificazione.Data.loc[index_oggi+1]#----------------------------------------dopodomani
#data_first = max(date(anno_corrente, mese_n, 3), next_working) # la prima data è DOMANI -------------------------------------------------------------------------
data_first = next_working
data_last = calendario_pianificazione.day_n.iloc[-1]
#---------------------------------------------------------------------------------correzione interventi senza tempo
media_intervento = mese[mese['Min']>0]['Min'].mean()
mese['Durata_stimata'] = np.where(mese['Min']>0, mese['Min'], media_intervento)

st.dataframe(mese)

chiusi = df_raw[df_raw.S == "C"]
chiusi_save = chiusi
chiusi['data_AB'] = pd.to_datetime(chiusi['Data Esecuzione'].str[0:10], format="%d/%m/%Y")
#chiusi['data_AB'] = pd.to_datetime([data[0:10] for data in chiusi['Data Esecuzione'].astype(str)], format="%d/%m/%Y")

chiusi = chiusi[['data_AB','key']]
chiusi = chiusi.reset_index(drop=True)
len_c = len(chiusi)
da_c = chiusi.data_AB.min().date()
a_c = chiusi.data_AB.max().date()

col1, col2, col3,col10,col20,col30 = st.columns([1,1,1,1,1,1])
with col1:
    st.title(f':orange[{len_c}]')
    st.write('Interventi chiusi dal {} al {}'.format(da_c,a_c))

pianificabile = mese[(mese.S == "F")  | (mese.S == "F*")]
pianificati = pianificabile[[(all(check not in word for check in filtro_pianificati)) and (word != 'nan') for word in pianificabile.Operatore.astype(str)]]
pianificati = pianificati[['Data Inizio','key']]
pianificati = pianificati.rename(columns={'Data Inizio':'data_AB'})
pianificati = pianificati.reset_index(drop=True)

len_p = len(pianificati)
da_p = pianificati.data_AB.min().date()
a_p = pianificati.data_AB.max().date()

with col3:
    st.title(f':white[{len_p}]')
    st.write('Interventi pianificati in attesa di esecuzione dal {} al {}'.format(da_p,a_p))

pianificabile = pianificabile[[(any(check in word for check in filtro_pianificati)) or (word == 'nan') for word in pianificabile.Operatore.astype(str)]]
pianificabile = pianificabile.reset_index(drop=True)

pianificabile = pianificabile[['ID','S','Data Inizio','Cliente','Sito','Indirizzo Sito','Dispositivi Installati','SitoTerritoriale','Servizio','ID Contratto','Codice Contratto','Citta',
                              'Operatore','Min','Periodicita','Operatore2','key','key_sito','key_univoca','Durata_stimata','IstruzioniOperative', 'Note','lat','lng']]

len_todo = len(pianificabile)
da_pian = pianificabile['Data Inizio'].min().date()
a_pian = pianificabile['Data Inizio'].max().date()

with col20:
    st.title(f':red[{len_todo}]')
    st.write('Interventi da pianificare dal {} al {}'.format(da_pian,a_pian))


# inizio elaborazione------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
# i calcoli sulla frequenza degli interventi vengono fatti sul dataframe del mese da pianificare.    
count_row = mese[['key','Periodicita']].groupby(by='key').count().sort_values(by='Periodicita', ascending = False)
count_row_distinct = mese[['key','Periodicita']].groupby(by='key').nunique().sort_values(by='Periodicita', ascending = False)
rank = mese[['key','Periodicita']]
rank['rank'] = rank.groupby('key').rank(method='dense')
sito = mese[['key_sito','ID']].groupby(by='key_sito').count()
chiusi = pd.concat([chiusi,pianificati]) #-------------------------------------considero chiusi + pianificati per calcolare l'ultima data
#st.write(chiusi)
#st.stop()


chiusi = chiusi.groupby(by='key').max()
pianificati = pianificati.groupby(by='key').max()

df_out = rank.merge(count_row, how='left', left_on='key', right_on='key')
df_out = df_out.rename(columns={'Periodicita_x':'Periodicita', 'Periodicita_y':'Conteggio'})
df_out = df_out.merge(count_row_distinct, how='left', left_on='key', right_on='key')
df_out = df_out.rename(columns={'Periodicita_x':'Periodicita', 'Periodicita_y':'Conteggio_distinti'})
df_out=df_out.merge(chiusi, how='left', left_on='key', right_on='key')
df_out = df_out.rename(columns={'data_AB':'ultimo_intervento'})
df_out=df_out.merge(pianificati, how='left', left_on='key', right_on='key')
df_out = df_out.rename(columns={'data_AB':'ultimo_pianificato'})
df_out['ultimo_intervento_check'] = df_out.ultimo_intervento.astype(str).replace({'NaT':'Pianificazione libera'})

df_out['Target'] = np.where(df_out.ultimo_intervento_check != 'Pianificazione libera', df_out.ultimo_intervento + timedelta(days = 30), np.datetime64('NaT'))

df_out['mese']=[data.month for data in df_out['Target']]
data_corretta = calendario_pianificazione.Data.iloc[-1]
for i in range(len(df_out)):
    if df_out.mese.iloc[i]!= mese_n:
        df_out.Target.iloc[i]=pd.to_datetime(data_corretta)

df_out = df_out.drop_duplicates()
df_out['key_univoca']=df_out.key + df_out.Periodicita

output = pianificabile[['ID','S','Data Inizio','Cliente','Sito','Indirizzo Sito','Servizio','key','key_sito','key_univoca','Durata_stimata']]
output = output.merge(df_out,how='left', left_on='key_univoca', right_on='key_univoca')
output = output.merge(sito, how='left', left_on='key_sito', right_on='key_sito')
output = output.sort_values(by=['Cliente','Sito','Periodicita','ID_y','rank'])
output = output.reset_index(drop=True)
output = output.rename(columns={'ID_y' : 'Servizi sul sito'})

colonne = output.columns

#output = output.loc[20:21] #-------------------------------------------------------------------------------------------------------------------------------------------------------------output filt

# Dataframe PLANNED--------------------------------------------------------------------------------------------------------------------------
planned = pd.DataFrame(columns=colonne)
planned['TGT_new']=[]
ultimo = {}

planned['last']=np.datetime64('NaT')
planned['periodo'] = 1
planned['range'] = None

st.write('Dataframe: Output')
st.dataframe(output)


for i in range(len(output)):
    frequenza = output['Conteggio_distinti'].iloc[i]
    periodo = math.floor(30/frequenza)
    rank = output['rank'].iloc[i]
    sito = output['key_sito'].iloc[i]  
    
    if frequenza == 1: # servizi previsti una sola volta nel mese        
        planned.loc[i]=output.iloc[i]
        if output['ultimo_intervento'].astype(str).iloc[i]=='NaT': #---------sono in stato di pianificazione libera e un singolo intervento
        #if output['ultimo_intervento_check'].astype(str).iloc[i]=='Pianificazione libera': #---------sono in stato di pianificazione libera e un singolo intervento    
            planned['TGT_new'].iloc[i]=date(anno_corrente,mese_n,15)
            #planned['TGT_new']=np.datetime64('NaT') 
        else: #------------distanzio di un mese dall'ultimo
            planned['TGT_new'].loc[i] = output['Target'].iloc[i] #---------distanziato 30gg 
    else:
        chiave = output['key_x'].iloc[i]
        periodo = 30/frequenza
        if output['rank'].iloc[i] == 1: # è il primo degli interventi multpli è il 1 di n
            planned.loc[i]=output.iloc[i]
            if output['ultimo_intervento'].astype(str).iloc[i]=='NaT':
                planned['TGT_new'].loc[i] = data_first
                ultimo[chiave] = planned['TGT_new'].loc[i]
            else:
                last = output['ultimo_pianificato'].iloc[i]
                if str(last)=='NaT':
                    last = output['ultimo_intervento'].iloc[i]
                planned['TGT_new'].loc[i] = last + timedelta(days = periodo)
                planned['last'].loc[i]=str(last)
                #planned['TGT_new'].loc[i] = data_first # oppure metto il target?
                ultimo[chiave] = planned['TGT_new'].loc[i]
        else:
            chiave = output['key_x'].loc[i]
            periodo = 30/frequenza
            try:
                last = ultimo[chiave]                 
            except:
                last = output['ultimo_pianificato'].iloc[i]
                if str(last)=='NaT':
                    last = output['ultimo_intervento'].iloc[i]

            if output.key_univoca.iloc[i] == output.key_univoca.iloc[i-1]: # per raggruppare sullo stesso giorno gli interventi dell'università
                tgt_new = planned.TGT_new.loc[i-1]
            else:
                tgt_new = last + timedelta(days = periodo)

            planned.loc[i]=output.iloc[i]
            if tgt_new.month == mese_n:
                planned['TGT_new'].loc[i] = tgt_new
            else:
                planned['TGT_new'].loc[i] = calendario_pianificazione.Data.iloc[-1]

            planned['last'].loc[i]=str(last)     
            ultimo[chiave] = tgt_new

    planned['periodo'].loc[i]=periodo
    
planned = planned.rename(columns={'ID_x':'ID'})
planned = planned[['ID','S','Data Inizio','Cliente','Sito','Indirizzo Sito','Servizio','Periodicita','rank','Conteggio','Conteggio_distinti','ultimo_intervento','ultimo_pianificato',
                   'ultimo_intervento_check','Target','Servizi sul sito','TGT_new','last','periodo','key_sito','Durata_stimata','range']]

st.subheader('Interventi scaduti', divider='orange')


#------------------------------------------------------------------------------------------------------da qui inizio il raggruppamento di disponibilità vicine 

planned['day']=[data.day for data in planned.TGT_new]


for i in range(len(planned)):   
    if planned['S'].iloc[i]=='F*': # metto il vincolo sulla data degli interventi improrogabili
        disp_intervento = [planned['Data Inizio'].iloc[i].day]
        planned['range'].iloc[i] = disp_intervento
    else:      
        periodo_intervento = planned.periodo.iloc[i]
        delta = deltas[periodo_intervento]
        giorno_tgt = planned.day.iloc[i]
        disp_intervento = np.arange(giorno_tgt-delta, giorno_tgt + delta, step=1)
        disp_adj = [elemento for elemento in disp_intervento if (elemento >= (data_first).day) & (elemento <= data_last) ] # per mettere prima data pianificata da oggi in poi
        

        if disp_adj != []:
            planned['range'].iloc[i] = disp_adj
        else:
            planned['range'].iloc[i] = np.arange(data_first.day,data_first.day+3,step=1) # riproposto in un range a partire dal primo giorno disponibile + 3 giorni 
            if planned.Target.astype(str).iloc[i] != 'nan':
                if planned.Target.iloc[i].month == mese_n and planned.Target.iloc[i].month is not None :
                    planned['range'].iloc[i] = np.arange(data_first.day,data_first.day+3,step=1) # riproposto in un range a partire dal primo giorno disponibile + 3 giorni 
                    st.write(f'Attenzione: intervento ID {planned.ID.iloc[i]} | :orange[Cliente: {planned.Cliente.iloc[i]} ]| fuori target - ripianificato ')
    
    if (planned['ultimo_intervento_check'].iloc[i]=='Pianificazione libera') and (planned['ultimo_intervento_check'].iloc[i]==30): # se non c'è vincolo metto disponibili tutti i giorni
        disp_intervento = np.arange(1,31, step=1)
        disp_adj = [elemento for elemento in disp_intervento if elemento >= (data_first).day]
        planned['range'].iloc[i] = disp_adj

    if planned['S'].iloc[i]=='F*': # metto il vincolo sulla data degli interventi improrogabili
        disp_intervento = [planned['Data Inizio'].iloc[i].day]
        planned['range'].iloc[i] = disp_intervento

planned_print=planned[['ID','Cliente','Indirizzo Sito','Servizio','Periodicita','ultimo_intervento','periodo','range']]
#planned_print['TGT_new']=planned_print['TGT_new'].astype(str)

st.divider()
st.write('**Date disponibili per interventi**')
st.dataframe(planned_print)

#–-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

planned['gruppo'] = None
planned['disp_new'] = None
gruppo = 1
planned['gruppo'].iloc[0]=gruppo
planned['disp_new'].iloc[0] = planned['range'].iloc[0]
for i in range(1,len(planned)):
    sito = planned['key_sito'].iloc[i] 
    if sito == planned['key_sito'].iloc[i-1]:
        comuni = list(set(planned.disp_new.iloc[i-1]) & set(planned.range.iloc[i])) # elementi comuni
        if comuni != []: # se ci sono elementi in comune
            planned['disp_new'].iloc[i] = comuni
            planned['gruppo'].iloc[i] = planned['gruppo'].iloc[i-1]
        else:
            planned['disp_new'].iloc[i] = planned['range'].iloc[i]
            gruppo += 1
            planned['gruppo'].iloc[i]=gruppo

    else:
         planned['disp_new'].iloc[i] = planned['range'].iloc[i]
         gruppo += 1
         planned['gruppo'].iloc[i]=gruppo


gruppi = planned[['gruppo','disp_new']].groupby(by='gruppo').last()
durata_gruppi = planned[['gruppo','Durata_stimata']].groupby(by='gruppo').sum() #-----------------------da mergiare con df
durata_gruppi = durata_gruppi.rename(columns={'Durata_stimata':'Durata_gruppo'})
count_gruppi = planned[['gruppo','ID']].groupby(by='gruppo').count()
count_gruppi = count_gruppi.rename(columns={'ID':'count_gruppo'})

planned = planned.merge(gruppi, how='left', left_on = 'gruppo',right_on='gruppo')
planned = planned.rename(columns={'disp_new_y':'available'})

date_target = planned[['ID','available','gruppo']]

#-----------------------------------------------------------------------------------------------------------------------------------------assegnazione agli operatori

colonne=['ID','Data Inizio','Cliente', 'Sito', 'Indirizzo Sito', 'SitoTerritoriale','Servizio','Periodicita','ID Contratto', 'Citta','Operatore','Operatore2','Durata_stimata','IstruzioniOperative','Note', 'lat','lng']



df = pianificabile[colonne]
df = df.merge(date_target, how='left', left_on='ID',right_on='ID')
df = df.rename(columns={'available':'Target_range'})
df = df.merge(ordine_siti, how='left', left_on='SitoTerritoriale', right_on='SitoTerritoriale')
df = df.merge(durata_gruppi, how='left', left_on='gruppo', right_on='gruppo')
df = df.merge(count_gruppi, how='left', left_on='gruppo', right_on='gruppo')

df['minimo'] = [min(intervallo) for intervallo in df.Target_range] # ordine crescente per data
df = df.sort_values(by=['SitoTerritoriale','Citta','minimo','Cliente'])
df['Stimato']=df['Durata_stimata']/60

df['allowed']=None
for i in range(len(df)):
    df['allowed'].iloc[i]=[0,1,2,3,4,5]

#------------------------------------------------------------------------------------------------------------ Disponibilità siti Clara
clara_allowed = pd.read_excel(path_clara).fillna(0)
clara_allowed['allowed']=None
for j in range(len(clara_allowed)):
    lista = []
    for i in [0,1,2,3,4,5]:
        if clara_allowed[i].iloc[j]=='x':
            lista.append(i)
    clara_allowed['allowed'].iloc[j]=lista
    lista=[]
        
clara_allowed = clara_allowed[['Sito','allowed']]   


#-----------------------
df['check'] = False
#------------------------------------------------------------------------------------------------------------ Recupero info disponibilità Clara
df = df.merge(clara_allowed, how='left', left_on='Sito', right_on='Sito')
df['allowed']=np.where(df.allowed_y.astype(str) != 'nan', df.allowed_y, df.allowed_x )
df=df.drop(['allowed_x','allowed_y'], axis=1)




#-------------------------------------------# INDIVISIBILITà GRUPPI

df = df.sort_values(by=['gruppo','ID'], ascending=False)
df['check']=False
for i in range(1,len(df)):
    if df['gruppo'].iloc[i]==df['gruppo'].iloc[i-1]:
        df['check'].iloc[i]=True
        df['Durata_gruppo'].iloc[i]=df['Durata_stimata'].iloc[i]
    else:
        df['check'].iloc[i]=False

#-----------------------------------------------------------------------------------------------



df['ID']=df['ID']*10 # così posso inserire i duplicati
df = df.sort_values(by=['Ordine_sito','Citta','gruppo','ID'],ascending=False)
df = df.reset_index(drop=True)
df['SitoTerritoriale'] = df.SitoTerritoriale.astype(str).replace({'nan':'Non_definito'})
df['Citta'] = df.Citta.astype(str).replace({'nan':'Non_definito'})
colonne_new = df.columns

altri_siti = df[['ID','Cliente','Sito','Indirizzo Sito','IstruzioniOperative','Note','Servizio','Periodicita','SitoTerritoriale','Citta','Durata_stimata','Target_range']]


#--------------------------------------------------------------------------------------------------------------------------FILTRO SOLO FERRARA 

selected = ['FERRARA ','PMI 1','PMI 2']
df = df[[(any(elemento in check for elemento in selected)) for check in df.SitoTerritoriale.astype(str)]]
altri_siti = altri_siti[[all(elemento not in cliente for elemento in selected) for cliente in altri_siti.SitoTerritoriale.astype(str)]]

#------------------------------------------------------------------------------------------------------------ COSTRUZIONE AGENDE

viaggio_ar= 0.5 #andata + ritorno
viaggio_medio=0.2

op = 1
index_giorno = 0
wl=0

limite = 7.5
# sdoppio le righe con wl < 1gg
 
#df['check'] = False
df['nota_AB']= None

#-------------------------------------------------------------duplicazione righe con durata > 1gg
for i in range(len(df)): 
    wl = df['Durata_stimata'].iloc[i] / 60 + viaggio_ar
    if (wl > limite) and (df['check'].iloc[i] == False) : # condizione per sdoppiare le righe di durata > 1gg

        y = len(df)

        df.loc[y] = df.iloc[i] 
        #durata_new = df['Durata_stimata'].iloc[i] - limite * 60 + viaggio_ar * 60 + 10
        durata_new = limite * 60 - viaggio_ar * 60
        df['Durata_stimata'].loc[y] = durata_new
        df['Stimato'].loc[y]=df['Durata_stimata'].loc[y]/60
        df['nota_AB'].loc[y] = 'con_seguito' # in modo da bloccare il successivo sulla data+1

        df.loc[y+1] = df.iloc[i]
        df['Durata_stimata'].loc[y+1] = df['Durata_stimata'].iloc[i] - durata_new
        df['Stimato'].loc[y+1]=df['Durata_stimata'].loc[y+1]/60
        df['ID'].loc[y+1] = df['ID'].iloc[i] - 1 # per metterlo successivo
        df['nota_AB'].loc[y+1]= 'segue'
        df['check'].loc[y+1]=True # non viene pianificato prima che sia pianificato suo padre (la prima parte del lavoro, che sbloccherà questa)
        df['check'].iloc[i]=True # così poi non viene più pianificata
        df = df.drop([i])
        df = df.sort_values(by=['Ordine_sito','Citta','ID'],ascending=False)
        df = df.reset_index(drop=True)           

#st.dataframe(df)
#st.stop()

pianificato = pd.DataFrame(columns=colonne_new)

pianificato['data']=None
pianificato['operatore']=None
pianificato['Ora_Inizio']=None
pianificato['Ora_Fine']=None
pianificato['N_op'] = None
pianificato['Op_vincolo'] = None
pianificato['wl']=0
pianificato['tgtrange']=None

df['check2']=None

assegnati = {1:[]}

sito = df.SitoTerritoriale.iloc[0]

cal = calendario_no_domeniche(mese_n,anno_corrente,op) 
contatore = 0

#st.dataframe(df)
#st.stop()

#df[['ID','lat','lng','Target_range']].to_csv('/Users/Alessandro/Documents/AB/Clienti/AB/Exera/Programmazione/clustering.csv')

#st.stop()
limite_dist = 10

wl=0
wl_gruppo=0
while not df.check.eq(True).all(): 

    st.write(f'iterazione{contatore} di 20')
    contatore+=1
    limite_dist+=5  # allargo la zona
    wl = 0
    wl_gruppo = 0
    if contatore == 100: #------------------------------------------------------------------------------------------------------------------------------
        break

    if contatore % 1 == 0:
        index_giorno += 1
        wl = 0
        wl_gruppo = 0


    #wl = viaggio_ar
    flag = 'inizio_giornata'

    if index_giorno < len(cal): 
        index_giorno = index_giorno
       
    else:
        index_giorno = 0
        op+=1 
        assegnati[op] = []
        cal = calendario_no_domeniche(mese_n,anno_corrente,op)
        wl = viaggio_ar
        
    giorno = cal.day.loc[index_giorno]
    giorno_n = cal.day_n.loc[index_giorno]
    log=[]

    for i in range(len(df)):
        delta_durata = 0      
        sito_terr = df.SitoTerritoriale.iloc[i]
        viaggioAR = viaggi[sito_terr]
        durata_gruppo = df.Durata_gruppo.iloc[i]/60
        #gruppo = df.gruppo.iloc[i]

        if df.check.iloc[i] == False:

            #if wl == viaggio_ar: #se l'operatore non ha ancora attività pianificate oltre al viaggio AR
            if flag == 'inizio_giornata':
                aggiunta = df.Stimato.iloc[i]+viaggioAR
                aggiunta_gruppo = durata_gruppo+viaggioAR
                #aggiunta = df.Durata_gruppo.iloc[i]/60
                wl +=  aggiunta
                wl_gruppo += aggiunta_gruppo                        
                inizio = datetime(2000, 1, 1, 8, 0, 0)   # può nascere un problema se il gruppo + viaggio è > 450 minuti-----------------------------

                # QUI INSERISCO LE COORDINATE DEL PRIMO SITO-----------------------------------------------------------------------------------------
                # righe senza cooordinate prendono il centro della città oppure il cliente preccedente
                # estraggo la lista di tutti i siti in cui ho il match di giornata
                # calcolo la distanza da 'sito_check' (intervento precedente)
                # calcolo il subset dei siti vicini (90p delle distanze) il 90 è da validare
                # condizione di inserimento insieme alla data. 

               
                

                #st.stop()
                lat_sito = df.lat.iloc[i]
                lng_sito = df.lng.iloc[i]
                coord_check = (lat_sito,lng_sito)
                limite_dist = 1

               # distanze = {}
                #for d in range(len(df)):
                #    if giorno in df.allowed.iloc[d]:
                  #      try:
                  #          distanze[df.ID.iloc[d]]=geopy.distance.geodesic(coord_check, (df.lat.iloc[d],df.lng.iloc[d])).km
                  #      except:
                   #         distanze[df.ID.iloc[d]]=100

               # distanze_ok = {k: v for k,v in distanze.items() if v < limite_dist}

              #  id_ok = list(distanze_ok.keys())
               
                                
            else:

                if df.gruppo.iloc[i] == df.gruppo.iloc[i-1]:
                    aggiunta = df.Stimato.iloc[i]
                    aggiunta_gruppo = durata_gruppo
                else:
                    aggiunta = df.Stimato.iloc[i] + viaggio_medio
                    aggiunta_gruppo = durata_gruppo + viaggio_medio

                wl += aggiunta
                wl_gruppo += aggiunta_gruppo

                #st.write('qui')
                inizio = fine + timedelta(hours = viaggio_medio)

                #prova-------

                #distanze = {}
                #for d in range(len(df)):
                 #   if giorno in df.allowed.iloc[d]:
                  #      try:
                   #         distanze[df.ID.iloc[d]]=geopy.distance.geodesic(coord_check, (df.lat.iloc[d],df.lng.iloc[d])).km
                    #    except:
                     #       distanze[df.ID.iloc[d]]=100

                #distanze_ok = {k: v for k,v in distanze.items() if v < limite_dist}

                #id_ok = list(distanze_ok.keys())

                #prova-------




            if contatore>990:
                log.append(f'i:{i} | ID:{df.ID.iloc[i]} | cliente:{df.Cliente.iloc[i]} wl:{wl} | op:{op}')


            if wl_gruppo <= limite: #era wl
                wl_gruppo = wl

                
                if (giorno in df.allowed.iloc[i]) and (giorno_n in df.Target_range.iloc[i]) and (df['ID'].iloc[i] not in assegnati[op]): #and (df['ID'].iloc[i] in id_ok): #  dizionario assegnati serve per non assegnare allo stesso OP una attività da 2 op              
                    df.check.iloc[i]=True
                    durata = df.Stimato.iloc[i]
                    fine = inizio + timedelta(hours = durata)  #---------pausa

                    if flag == 'inizio_giornata':
                        #wl_gruppo = wl
                        flag='libero'

                    if (inizio.hour <= 12) and (fine.hour >= 12):
                        fine = fine + timedelta(hours = 1.5)
                    else:
                        fine = fine

                    l=len(pianificato)
                    pianificato.loc[l] = df.iloc[i]
                    pianificato.data.loc[l]=cal.Data.iloc[index_giorno]
                    pianificato.operatore.loc[l]=cal.operatore.iloc[index_giorno]  
                    pianificato.Ora_Inizio.loc[l] = inizio.time()
                    pianificato.Ora_Fine.loc[l] = fine.time()
                    pianificato['wl'].loc[l]=wl
                    pianificato['tgtrange'].loc[l] = df.Target_range.iloc[i]
                    df['check2'].iloc[i]='pianificato'
                    assegnati[op].append(df['ID'].iloc[i])

                    gruppo = df.gruppo.iloc[i]
                   
                    #lat_sito = df.lat.iloc[i]
                    #lng_sito = df.lng.iloc[i]
                    #coord_check = (lat_sito,lng_sito)
                    #limite_dist = 1
                    







                    for n in range(len(df)):
                        gruppo_check = df.gruppo.iloc[n]
                        if (gruppo_check == gruppo) and (df['check2'].iloc[n] != 'pianificato'):
                            df.check.iloc[n]=False
                            #df['Target_range'].iloc[n] = [giorno_n]
                            #if df.Cliente.iloc[n] == 'ORI FRIGO SRL':
                                #st.write(df)
                                #st.write(pianificato)
                               # st.stop()
                    
                    
                    if df['nota_AB'].iloc[i] == 'con_seguito': #metto la data +1 alla seconda tranche del lavoro
                        df['nota_AB'].iloc[i] = 'eseguito'
                        id_collegato = df.ID.iloc[i] - 1
                        new_range = [cal.Data.iloc[index_giorno+1].day]
                        for j in range(len(df)):
                            if df.ID.iloc[j] == id_collegato:
                                df['Target_range'].iloc[j] = new_range
                                df['check'].iloc[j]=False # rendo pianificabile la seconda parte di lavoro------------------------------------------------------------------questo era il bug 
                                df['nota_AB'].iloc[j]='eseguito'
                                #st.write(df.iloc[j])

                        st.write(df[df.ID == id_collegato ])


                    if (df['Operatore'].iloc[i]==' 2 OPERATORI'):# and (df['nota_AB'].iloc[i] != 'processato'):
                        df['Operatore'].iloc[i] = '2OP|gia splittato'
                        pianificato['N_op'].loc[l]='2 OPERATORI'
                        pianificato['Op_vincolo'].loc[l]=df['Operatore2'].iloc[i]

                        pos = len(df) 
                        #df['Target_range'].iloc[i]=[cal.Data.iloc[index_giorno].day]
                        df['Target_range'].iloc[i]=[pianificato.data.loc[l].day] # gli assegno la data appena assegnata
                        df.loc[pos] = df.iloc[i] # duplico la riga per poterla assegnare a un secondo operatore
                        #df['Target_range'].loc[pos] = [cal.Data.iloc[index_giorno].day]
                        df['check'].loc[pos] = False
                        df['Operatore'].loc[pos] = '2OP|elaborato'

                    if df['Operatore'].iloc[i]==' VINCOLO ,':
                        pianificato['Op_vincolo'].loc[l]=df['Operatore2'].iloc[i]
                    if df['Operatore'].iloc[i]=='2OP|elaborato':
                        pianificato['N_op'].loc[l]='2 OPERATORI'
                else:
                    wl -= aggiunta
                    wl = np.round(wl,2)
                    wl_gruppo -= aggiunta_gruppo
                    
            else:
                wl -= aggiunta  # tolgo il wl della riga e vado avanti 
                wl = np.round(wl,2)
                wl_gruppo -= aggiunta_gruppo

st.subheader('Agenda interventi',divider='orange')
#st.write('Dataframe: pianificato')                
#st.dataframe(pianificato[['ID','data','Ora_Inizio','Ora_Fine','Cliente','Sito','Servizio','Periodicita','SitoTerritoriale','Citta','operatore','N_op','Op_vincolo','Durata_stimata','wl','tgtrange']],width=2500)

st.dataframe(pianificato[['ID','data','Cliente','Sito','Servizio','Periodicita','SitoTerritoriale','Citta','operatore','N_op','Op_vincolo','Durata_stimata','wl','tgtrange']],width=2500)
#st.write(f'ciclo completo dopo {contatore} iterazioni')

st.divider()
st.subheader('non pianificati')
st.dataframe(df[df.check==False])

visualizzazione = pianificato[['ID','data','operatore','Cliente','Sito','Indirizzo Sito','IstruzioniOperative','Note','Servizio','Periodicita','SitoTerritoriale','Citta','N_op','Op_vincolo','Durata_stimata','tgtrange']]
visualizzazione = visualizzazione.rename(columns={'Note':'Note_old'})
visualizzazione['Note'] = np.where(['Visita' not in nota for nota in visualizzazione['Note_old'].astype(str)],visualizzazione['Note_old'],'')
visualizzazione = visualizzazione.drop('Note_old',axis=1)

visualizzazione = visualizzazione.sort_values(by=['data','operatore','Cliente'])
visualizzazione = visualizzazione.reset_index(drop=True)
visualizzazione.to_excel(('/Users/Alessandro/Documents/AB/Clienti/AB/Exera/Programmazione/proposta pianificazione al {}_SOLO FERRARA.xlsx'.format(oggi)))

vincolo_nop = visualizzazione[['ID','N_op','Op_vincolo']]
altri_siti  = altri_siti.merge(vincolo_nop, how='left',left_on='ID',right_on='ID')
altri_siti.to_excel(('/Users/Alessandro/Documents/AB/Clienti/AB/Exera/Programmazione/altri_siti.xlsx'))