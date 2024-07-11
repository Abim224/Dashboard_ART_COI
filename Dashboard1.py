# -*- coding: utf-8 -*-
"""
Created on Thu Jul  4 19:15:26 2024

@author: Abinash.m
"""


import pandas as pd
import requests
import io
from datetime import datetime,timedelta
import numpy as np
from datetime import datetime
import pytz
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt

from streamlit_option_menu import option_menu
import time
from streamlit_extras.metric_cards import style_metric_cards
import schedule

st.set_page_config(
    page_title="Ex-stream-ly Cool App",
    page_icon="👩‍💻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

agent_df = pd.read_excel("./TL Mapping for COI.xlsx")
agent_df = agent_df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
agent_df.replace('-', 'OFF', inplace=True)
agent_df.replace(np.nan, 'OFF', inplace=True)

def API():
    url ="https://home-c45.nice-incontact.com/ReportService/DataDownloadHandler.ashx?CDST=C3JXgBEguvxxk7vTBugMOa258ohbohd20s%2fVo46V9QYM71x9zXk%2f9YOcTGZQ%2bDNG0DcqfqmmckZjjwQK%2b9mFpRbSD%2bT370c5mwLiPOTbHU02R%2bzc%2fUOMXaWR%2fQkpWn%2beTE6hyRUpyCyjZ%2fzUkeZb6BZd5UJr8ZiqGFUspzF2e7pP8J6rNp29sRB2%2b%2bx1oC0S3usc02iljryQ9rIGvsyMgeNMbk43lyK1haCqz9aZpMxi8MNAb8x7&PresetDate=1&Format=CSV&IncludeHeaders=True&AppendDate=False"
    my_urls = [url]
    final_df = pd.DataFrame()
    for my_url in my_urls:
        response = requests.get(my_url, stream=True)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            df = df.sort_values(by=['agent_no', 'start_date'])
            final_df = pd.concat([final_df, df], ignore_index=True)
        else:
            print(f"Failed to fetch data from {my_url}")
    agent_id_list=agent_df['agent_no'].unique().tolist()
    mask =final_df['agent_no'].isin(agent_id_list)
    final_ldl_df = final_df[mask] 
    
    return final_ldl_df
final_ldl_df= API()
agent_shift = agent_df
agent_shift1 =agent_shift.copy()
melted_df = pd.melt(agent_shift, id_vars=['agent_no','Name','TM name','Location'], 
                    var_name='Shift_Date', value_name='Value')
final_ldl_df['start_date']= pd.to_datetime(final_ldl_df['start_date']).dt.strftime('%Y-%m-%d')
mnth = datetime.today().month
if mnth<10:
    mnth = "0"+str(mnth)
if datetime.today().day<=9:
    val = '0'+str(datetime.today().day)
else:
    val =datetime.today().day
current_day = str(datetime.today().year)+"-"+str(mnth)+"-"+str(val)
def convert_to_12hr_format(time_range):
    try:
        start_time, end_time = time_range.split(' - ')
        start_time = datetime.strptime(start_time.strip(), '%H:%M').strftime('%I:%M %p')
        end_time = datetime.strptime(end_time.strip(), '%H:%M').strftime('%I:%M %p')
        return f"{start_time} - {end_time}"
    except:
        return time_range

melted_df['Value'] = melted_df['Value'].apply(convert_to_12hr_format)
final_ldl_df = final_ldl_df[final_ldl_df['start_date']==current_day]
merge_agent_shift = pd.merge(melted_df,final_ldl_df,on='agent_no',how='inner')
merge_agent_shift.fillna('N/A',inplace=True)
merge_agent_shift_for_current = merge_agent_shift[(merge_agent_shift['Shift_Date']==current_day) &( (merge_agent_shift['start_date']==current_day) | (merge_agent_shift['start_date']=='N/A'))]
merge_agent_shift_for_current[['Start_Time', 'End_Time']] = merge_agent_shift_for_current['Value'].str.split(' - ', expand=True)

merge_agent_shift_for_current['End_Time'] = np.where(merge_agent_shift_for_current['Start_Time'].isin(['OFF', 'N/A', 'PL']), 
                                                     merge_agent_shift_for_current['Start_Time'], 
                                                     merge_agent_shift_for_current['End_Time'])
total_agents = len(merge_agent_shift_for_current['agent_no'].unique().tolist())
team_members_count = merge_agent_shift_for_current.groupby('TM name')['Name'].nunique().reset_index(name='members_count')
merge_agent_shift_for_current.columns
agents_off_today = merge_agent_shift_for_current[merge_agent_shift_for_current['Value'] == 'OFF'].groupby('TM name')['agent_no'].nunique().reset_index(name='agents_off')
worked_hours = merge_agent_shift_for_current[((merge_agent_shift_for_current['agent_state_code'] >= 0)&(merge_agent_shift_for_current['agent_state_code'] <= 50))&(merge_agent_shift_for_current['Value'] != 'OFF')].groupby('TM name')['duration'].sum().reset_index(name='total_worked_hours')
break_time = merge_agent_shift_for_current[((merge_agent_shift_for_current['agent_state_code'] <= 0)|(merge_agent_shift_for_current['agent_state_code'] > 50))& (merge_agent_shift_for_current['Value'] != 'OFF')].groupby('TM name')['duration'].sum().reset_index(name='total_break_time')
result = team_members_count.merge(agents_off_today, on='TM name', how='left') \
                           .merge(worked_hours, on='TM name', how='left') \
                           .merge(break_time, on='TM name', how='left')
scheduled_for_today = total_agents-   int(agents_off_today['agents_off'].sum())                       
                          
# result.fillna(0, inplace=True)  
st.markdown("<h1 style='text-align: center; color: red;'>Overall Information</h1>", unsafe_allow_html=True)
col1, col2, col3, col4, col5, col6 ,col7,col8= st.columns(8)
with col1:
    st.metric(label="Total Teams :male-office-worker:",value=f"{len(team_members_count['TM name'].unique()):,.0f}")

with col2:
    st.metric(label="Total Agents :male-technologist:",value=f"{total_agents:,.0f}")

with col3:
    st.metric(label="Scheduled for today :man_with_probing_cane:",value=f"{ scheduled_for_today:,.0f}")

with col4:
    st.metric(label="PTO / Leave",value=f"{int((agents_off_today['agents_off'].sum())):,.0f}")

with col5:
    st.metric(label="Total Hours Logged in MTD :male-office-worker:",value=f"""{ int(worked_hours['total_worked_hours'].sum())/3600:,.0f} """)
with col6:
    st.metric(label="Total Hours logged in current Day: ❌",value=f""" { int(break_time['total_break_time'].sum())/3600:,.0f}""")
with col7:
    st.metric(label="On floor :male-office-worker:",value=f"""{ int(worked_hours['total_worked_hours'].sum())/3600:,.0f} """)
with col8:
    st.metric(label="On Break ❌",value=f""" { int(break_time['total_break_time'].sum())/3600:,.0f}""")

style_metric_cards(background_color="#FFFFFF",border_left_color="#686664",border_color="#000000",box_shadow="#F71938")
# st.title('Team Performance Metrics')

col1, col2  = st.columns(2)

with col1:
    # st.header('Team Wise Number of Associates')
    result_sorted = result.sort_values('members_count', ascending=False)
    fig1 = px.bar(result_sorted, x='TM name', y='members_count', title='Headcount vs Scheduled',
                  labels={'members_count': 'Number of Associates', 'TM name': 'Team Name'},
                  text='members_count')
    fig1.update_traces(textposition='outside')
    fig1.update_layout(margin=dict(t=40, b=40), height=400)
    st.plotly_chart(fig1)

# Chart 2: Team wise number of associates on leave
with col2:
    # st.header('Team Wise Number of Associates on Leave')
    result_sorted = result.sort_values('agents_off', ascending=False)
    fig2 = px.bar(result_sorted, x='TM name', y='agents_off', title='Available vs Unavailable',
                  labels={'agents_off': 'Number of Associates on Leave', 'TM name': 'Team Name'},
                  text='agents_off')
    fig2.update_traces(textposition='outside')
    fig2.update_layout(margin=dict(t=40, b=40), height=400)
    st.plotly_chart(fig2)

# Create two more columns
col3, col4 = st.columns(2)

# Chart 3: Team wise number of associates working hours
with col3:
    # st.header('Team Wise Number of Associates Working Hours')
    result_sorted = result.sort_values('total_worked_hours', ascending=False)
    fig3 = px.bar(result_sorted, x='TM name', y='total_worked_hours',title='Total Worked Hours',
                  labels={'total_worked_hours': 'Total Working Hours', 'TM name': 'Team Name'},
                  text='total_worked_hours')
    fig3.update_traces(textposition='outside')
    fig3.update_layout(margin=dict(t=40, b=40), height=400)
    st.plotly_chart(fig3)

# Chart 4: Team wise number of associates on break
with col4:
    # st.header('Team Wise Number of Associates on Break')
    result_sorted = result.sort_values('total_break_time', ascending=False)
    fig4 = px.bar(result_sorted, x='TM name', y='total_break_time', title='Total Break Hours',
                  labels={'total_break_time': 'Total Break Time', 'TM name': 'Team Name'},
                  text='total_break_time')
    fig4.update_traces(textposition='outside')
    fig4.update_layout(margin=dict(t=40, b=40), height=400)
    st.plotly_chart(fig4)
