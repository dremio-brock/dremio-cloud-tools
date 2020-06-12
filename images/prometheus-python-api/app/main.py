import os, uuid, logging, sys, configparser, pandas as pd, pyarrow.parquet as pq
from base64 import b64encode
from prometheus_api_client import PrometheusConnect
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from azure.storage.blob.blockblobservice import BlockBlobService
from io import BytesIO

def write_pandas_dataframe_to_blob(blob_service, df, container_name, blob_name):
    buffer = BytesIO()
    df.to_parquet(buffer, allow_truncated_timestamps=True)
    blob_service.create_blob_from_bytes(
        container_name=container_name, blob_name=blob_name+'.parquet', blob=buffer.getvalue()
    )

def timed_job():
    config = configparser.ConfigParser()
    config.read('config/config.cfg')
    account=config.get('DEFAULT','ACCOUNT')
    key=config.get('DEFAULT','KEY')
    promi=config.get('DEFAULT','PROM')
    promup=promi.encode()
    container=config.get('DEFAULT','CONTAINER')
    url=config.get('DEFAULT','URL')
    blob_service = BlockBlobService(account_name=account, account_key=key)
    userAndPass = b64encode(promup).decode("ascii")
    headers = { 'Authorization' : 'Basic %s' %  userAndPass }

    prom = PrometheusConnect(url=url, headers=headers, disable_ssl=False)
    metric_data = prom.all_metrics()

    time = datetime.now()
    metrics=[]
    values=[]

    for i in metric_data:
        metric = prom.get_metric_range_data(metric_name=i, start_time=time-timedelta(hours=1), end_time=time, chunk_size=timedelta(hours=1))
        x=int(0)
        for d in metric:
            for name, dct in d.items():
                dct=dict(dct)
                if name == 'metric':
                    dct['id']=x
                    metrics.append(dct)
                else:
                    for key in dct:
                        va={}
                        va['time'] = key
                        va['value'] = dct[key]
                        va['id'] = x
                        values.append(va)
                        x=x+1

    df = pd.DataFrame(metrics)
    df1 = pd.DataFrame(values)
    df = pd.merge(df, df1, how='inner', left_on=['id'], right_on = ['id'])
    df['time'] = pd.to_datetime(df['time'],unit='s')

    df = df.drop(['endpoint', 'service', 'id'], axis=1)
    write_pandas_dataframe_to_blob(blob_service, df, container, str((datetime.now()).date())+'/'+str(datetime.now().time()).replace(':', '').replace(".", ''))

if __name__ == "__main__":
    sched = BlockingScheduler()
    sched.add_job(timed_job, 'interval', hours=1)
    sched.start()
