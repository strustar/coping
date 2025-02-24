import pandas as pd
import numpy as np
import streamlit as st
from shapely.geometry import Polygon

def get_coping_data(uploaded_file=None):
    if uploaded_file is None:  # 업로드된 파일이 없으면 기본 파일 읽기        
        df = pd.read_excel("coping_input.xlsx", sheet_name=0, header=None, engine="openpyxl")
    else:  # 업로드된 파일이 있으면 그 파일 읽기
        df = pd.read_excel(uploaded_file, sheet_name=0, header=None)
    arr = df.fillna('').to_numpy().astype(str)  # ✅ Numpy 배열 변환 (성능 향상)    
    # st.write(arr)

    # ✅ 키워드별 데이터 처리 규칙 (공통 처리)
    keyword_config = {
        'length': ('x', 'y', 'z'),
        'coping': ('xz'),
        'coping_z': ('z1', 'z2', 'z3'),
        'coping_x': ('x1', 'x2', 'x3'),
        'coping_cover': ('thickness',),    # tuple로 ,사용
        'rebar_x': (''),
        'rebar_y': (''),
        'rebar_z': (''),

        'column': ('height', 'diameter', 'cover'),
        'column_rebar': ('dia', 'num', 'layer', 'length_top', 'length_rebar'),
        'column_cross': ('dia', 'num', 'spacing', 'length_bottom'),
        'column_tie': (''),

        'footing': ('height', 'cover_upper', 'cover_lower', 'length_x', 'length_y', 'cover_xy', 'ver_dia', 'v_num', 'v_spacing'),
        'footing_ver': ('v1', 'v2', 'v3', 'v4', 'v5', 'v6'),
        'footing_top': (''),
        'footing_bottom': (''),
    }

    concrete_data = {}    # ✅ 공통 데이터 추출 함수
    def extract_data(keyword, keys):
        mask = np.char.lower(np.char.strip(arr)) == keyword.lower()
        
        if mask.any():
            row_idx, col_idx = np.where(mask)
            row, col = row_idx[0], col_idx[0]

            if keyword == 'coping':
                # Coping은 표 형태 추출
                points = df.iloc[row+1:row+9, col+1:col+3].dropna().values
                return {'xz': points}
            elif keyword in ['rebar_x', 'rebar_y', 'rebar_z', 'column_tie', 'footing_top', 'footing_bottom']:
                # rebar_x는 표 형태 추출
                points = df.iloc[row+1:row+5, col+1:col+8].values
                return {'': points}
            else:
                # 일반적인 key-value 추출
                values = [df.iloc[row+i+1, col+1] for i in range(len(keys))]
                return dict(zip(keys, values))

    # ✅ 키워드별 반복 처리
    for keyword, keys in keyword_config.items():
        result = extract_data(keyword, keys)
        if result:
            concrete_data[keyword.lower()] = result            


    ### 코핑 콘크리트 내부 라인(점) 추출
    outer = Polygon(concrete_data['coping']['xz'])    
    inner = outer.buffer(-concrete_data['coping_cover']['thickness'], join_style=2)  # 안쪽(음수) 오프셋 120mm 생성
    
    # Shapely 결과 → NumPy 변환 ===
    inner_points = np.array(inner.exterior.coords)    
    inner_points = inner_points[::-1]   # 기본 시계방향(buffer 기본)을 반시계방향으로 변환
    
    concrete_data['coping']['xz_inner'] = inner_points

    # 3차원 좌표 생성  (# 1번 위치(y좌표)에 0 삽입)
    concrete_data['coping']['xyz'] = np.insert(concrete_data['coping']['xz'], 1, 0, axis=1)  
    concrete_data['coping']['xyz_inner'] = np.insert(concrete_data['coping']['xz_inner'], 1, 0, axis=1)
    # 내부 맨 우측 피복 두께 만큼 이동
    concrete_data['coping']['xyz_inner'][5][0] += concrete_data['coping_cover']['thickness']
    concrete_data['coping']['xyz_inner'][6][0] += concrete_data['coping_cover']['thickness']

    return concrete_data


    