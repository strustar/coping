import re
import pyvista as pv
import numpy as np
import pandas as pd
import streamlit as st
from copingFcn import create_rebar, find2_point

def coping_rebar(rebar_scale, concrete_data):
    length = concrete_data['length']
    cover = concrete_data['coping_cover']['thickness']
    inner_points = concrete_data['coping']['xyz_inner']
    column = concrete_data['column']

    rebar_dict = {}  # (종류, 직경)을 key로 하고, [mesh, mesh, ...]를 value로 하는 딕셔너리
    def add_rebar(r_type, dia, mesh):
        rebar_dict.setdefault((r_type, dia), []).append(mesh)

    # ----------------------------------------------------
    # 1) 최외곽 리바 (outer)
    # ----------------------------------------------------
    dia = 29
    lines = []
    for i in range(len(inner_points) - 1):
        if i == 5:
            continue

        rebar = create_rebar(
            rebar_scale,
            start_point=inner_points[i, :],
            end_point=inner_points[i+1, :],
            r_outer=dia/2
        )
        lines.append(rebar)

    add_rebar('coping_outer', dia, pv.merge(lines))


    # ----------------------------------------------------
    # 2) y 방향 리바
    # ----------------------------------------------------
    rebar_y = concrete_data['rebar_x']['']  # (개수, 간격, dia)
    x_distance = 0
    for c, spacing, dia_str in zip(rebar_y[0], rebar_y[1], rebar_y[3]):
        if any(pd.isna(v) for v in (c, spacing, dia_str)):
            break

        dia = float(re.findall(r'\d+', dia_str)[0])
        lines = []
        for _ in range(int(c)):
            x_distance += spacing
            rebar = create_rebar(
                rebar_scale,
                start_point=(-length['x'] + x_distance, cover, length['z']),
                end_point=(-length['x'] + x_distance, length['y'] - cover, length['z']),
                r_outer=dia/2
            )
            lines.append(rebar)

        add_rebar('coping_y', dia, pv.merge(lines))

    # ----------------------------------------------------
    # 3) x / z 방향 (xz 평면 리바)
    #    - 원본 코드에서는 r_outer=25/2 고정
    #    - 직경 25로 처리 → (x, 25.0), (z, 25.0)
    # ----------------------------------------------------    
    for idx in range(2):
        r_type = 'coping_z' if idx == 0 else 'coping_x'
        if idx == 0:
            data_r = concrete_data['rebar_x']['']
            x0, x1 = -length['x'] + cover, 0
            z0, z1 = -99999, 99999
        else:
            data_r = concrete_data['rebar_z']['']
            x0, x1 = -99999, 99999
            z0, z1 = length['z'] - cover, 0

        x_distance, z_distance = 0, 0        
        for c, spacing, dia_str in zip(data_r[0][1:], data_r[1][1:], data_r[2][1:]):
            if any(pd.isna(v) for v in (c, spacing)):
                break

            lines = []
            dia = float(re.findall(r'\d+', dia_str)[0])
            for _ in range(int(c)):
                if idx == 0:
                    x_distance += spacing
                else:
                    z_distance += spacing

                line_p0 = np.array([x0 + x_distance, 0, z0 - z_distance], dtype=np.float32)
                line_dir = np.array([x1, 0, z1], dtype=np.float32)
                intersections = find2_point(concrete_data, line_p0, line_dir)
                if len(intersections) == 2:
                    rebar = create_rebar(
                        rebar_scale,
                        start_point=intersections[0],
                        end_point=intersections[1],
                        r_outer=dia/2  # 직경 25
                    )
                    lines.append(rebar)

            add_rebar(r_type, dia, pv.merge(lines))

    # ----------------------------------------------------
    # 4) 복사(translate) 로직
    #    - (a) outer, x, z, outer 리바를 y방향으로 복사
    #        translate 후 병합 → 다시 같은 키((r_type, dia))로 덮어쓰기
    #
    #    - (b) y리바를 z방향으로 복사
    #      → (y, dia) 메시에 대해 translate → 병합 → 다시 (y, dia)로 저장
    # ----------------------------------------------------

    # (a) outer / x / z → y방향 복사
    rebar_y_data = concrete_data['rebar_y']['']  # (개수, 간격) 정보
    for loop_type in ['coping_outer', 'coping_z', 'coping_x']:       # 세 종류를 각각 순회
        for (r_type, dia) in list(rebar_dict.keys()):        
            if r_type != loop_type:
                continue

            # merge 후 복사
            base_merged = pv.merge(rebar_dict[(r_type, dia)])
            rebar = []
            y_distance = 0
            for c, spacing in zip(rebar_y_data[0], rebar_y_data[1]):
                if any(pd.isna(v) for v in (c, spacing)):
                    break
                for _ in range(int(c)):
                    y_distance += spacing
                    copied = base_merged.copy(deep=True)
                    copied.translate((0, y_distance, 0), inplace=True)
                    rebar.append(copied)
            
            rebar_dict[(r_type, dia)] = [pv.merge(rebar)]   # 기존 데이터 삭제 (여기서는 이게 맞음)
            # add_rebar(r_type, dia, pv.merge(rebar))      # 기존 철근을 유지하면서 추가 (+=)


    # (b) y 리바 → z방향 복사
    rebar_z_data = concrete_data['rebar_z']['']
    for (r_type, dia) in list(rebar_dict.keys()):        
        if r_type != 'coping_y':            
            continue

        # merge 후 복사
        base_merged = pv.merge(rebar_dict[(r_type, dia)])
        rebar = []
        z_distance = 0
        for c, spacing in zip(rebar_z_data[0][:2], rebar_z_data[1][:2]):
            if any(pd.isna(v) for v in (c, spacing)):
                break
            for _ in range(int(c)):
                z_distance += spacing
                copied = base_merged.copy(deep=True)
                copied.translate((0, 0, -z_distance), inplace=True)
                rebar.append(copied)

        rebar_dict[(r_type, dia)] = [pv.merge(rebar)]


    # ----------------------------------------------------
    # 기둥 주철근 & 띠철근 & cross rebar
    # ----------------------------------------------------
    column_rebar = concrete_data['column_rebar']
    column_cross = concrete_data['column_cross']
    column_tie = concrete_data['column_tie']['']  # (개수, 간격, dia)
    footing = concrete_data['footing']
    num_lines = column_rebar['num']
    diameter = column['diameter'] - column['cover'] * 2
    height = column['height']

    outer_points = concrete_data['coping']['xyz']

    xc = (outer_points[2][0] + outer_points[3][0]) / 2
    center_top = (xc, length['y']/2, height/2 + column_rebar['length_top'])
    center_bottom = (xc, length['y']/2, -height/2 - column_cross['length_bottom'])

    ### 기둥 주철근
    dia = column_rebar['dia']
    for iter in range(2):
        if iter == 0:
            radius = diameter/2
        else:
            radius = diameter/2 - dia

        lines = []
        for i in range(int(num_lines)):
            angle = 2 * np.pi * i / num_lines
            x = radius * np.cos(angle) + xc
            y = radius * np.sin(angle) + length['y']/2
            start = (x, y, -column['height']/2 - footing['height'] + footing['cover_lower'])
            end   = (x, y, column['height']/2 + column_rebar['length_top'])

            rebar = create_rebar(rebar_scale, start_point=start, end_point=end, r_outer=dia/2)
            lines.append(rebar)

        if iter == 0:
            column_rebar1 = pv.merge(lines)            
        else:            
            column_rebar2 = pv.merge(lines)            
    
    column_rebar = pv.merge([column_rebar1, column_rebar2])
    add_rebar('column_rebar', dia, column_rebar)    

    ### 기둥 cross rebar
    lines = []
    angles_deg = [0, 45, 90, 135]
    dia = column_cross['dia']
    for iter in range(20):
        for deg in angles_deg:    
            rad = np.radians(deg)  # 각도를 라디안으로 변환
            z0 = column_cross['spacing'] * iter
            if center_bottom[2] + z0 > height/2:
                break
            # 원의 경계 양쪽 점 계산
            p1 = center_bottom + diameter/2 * np.array([np.cos(rad), np.sin(rad), 0]) + np.array([0, 0, z0])
            p2 = center_bottom - diameter/2 * np.array([np.cos(rad), np.sin(rad), 0]) + np.array([0, 0, z0])

            rebar = create_rebar(rebar_scale, start_point=p1, end_point=p2, r_outer=dia/2)
            lines.append(rebar)
        
    add_rebar('column_cross', dia, pv.merge(lines))

    ### 기둥 띠철근
    z_distance = 0
    for c, spacing, dia_str in zip(column_tie[0], column_tie[1], column_tie[2]):
        if any(pd.isna(v) for v in (c, spacing, dia_str)):
            break
        
        lines = []
        dia = float(re.findall(r'\d+', dia_str)[0])
        for _ in range(int(c)):
            z_distance += spacing

            profile = pv.Polygon(center=(diameter/2 + (22+25)/2, 0, 0), radius=dia/2,
                        normal=(0, 1, 0), n_sides=30, fill=False)

            # 띠철근 회전 (기둥 축을 기준으로 회전)
            extruded = profile.extrude_rotate(resolution=40, rotation_axis=(0, 0, 1))
            copied = extruded.copy(deep=True)
            copied.translate((center_top[0], center_top[1], center_top[2] - z_distance), inplace=True)
            lines.append(copied)

        add_rebar('column_tie', dia, pv.merge(lines))

    # ----------------------------------------------------
    # 기초 철근
    # ----------------------------------------------------
    footing_top = concrete_data['footing_top']['']
    footing_bottom = concrete_data['footing_bottom']['']
    footing = concrete_data['footing']
    # st.write(footing)

    for iter in range(2):
        if iter == 0:
            footing_rebar = footing_top
        else:
            footing_rebar = footing_bottom
        
        xy_distance = 0
        for c, spacing, dia_str in zip(footing_rebar[0], footing_rebar[1], footing_rebar[2]):
            if any(pd.isna(v) for v in (c, spacing, dia_str)):
                break

            lines = []
            dia = float(re.findall(r'\d+', dia_str)[0])
            if iter == 0:
                z0 = -height/2
            else:
                z0 = -height/2 - footing['height']

            for _ in range(int(c)):
                xy_distance += spacing
                for i in range(2):                
                    if i == 0:
                        x0 = center_bottom[0] - footing['length_x']/2 + footing['cover_xy']
                        x1 = center_bottom[0] + footing['length_x']/2 - footing['cover_xy']
                        y0 = center_bottom[1] - footing['length_y']/2 + xy_distance
                        y1 = y0
                    else:
                        x0 = center_bottom[0] - footing['length_x']/2 + xy_distance
                        x1 = x0
                        y0 = center_bottom[1] - footing['length_y']/2 + footing['cover_xy']
                        y1 = center_bottom[1] + footing['length_y']/2 - footing['cover_xy']

                    rebar = create_rebar(
                        rebar_scale,
                        start_point=(x0, y0, z0),
                        end_point=(x1, y1, z0),
                        r_outer=dia/2
                    )
                    lines.append(rebar)

            if iter == 0:
                add_rebar('footing_top', dia, pv.merge(lines))
            else:
                add_rebar('footing_bottom', dia, pv.merge(lines))


    # ----------------------------------------------------
    ### 복사
    footing_v = np.array(list(concrete_data['footing_ver'].values()))
    for (r_type, dia) in list(rebar_dict.keys()):        
        if r_type != 'footing_top':            
            continue

        base_merged = pv.merge(rebar_dict[(r_type, dia)])
        rebar = []
        z_distance = 0
        for iter in range(3):
            spacing = footing_v[iter]
            z_distance += spacing
            copied = base_merged.copy(deep=True)
            copied.translate((0, 0, -z_distance), inplace=True)
            rebar.append(copied)

        rebar_dict[(r_type, dia)] = [pv.merge(rebar)]

    for (r_type, dia) in list(rebar_dict.keys()):        
        if r_type != 'footing_bottom':            
            continue

        base_merged = pv.merge(rebar_dict[(r_type, dia)])
        rebar = []
        z_distance = 0
        for iter in range(2):
            spacing = footing_v[-iter-1]
            z_distance += spacing

            copied = base_merged.copy(deep=True)
            copied.translate((0, 0, z_distance), inplace=True)
            rebar.append(copied)

        rebar_dict[(r_type, dia)] = [pv.merge(rebar)]


    ### 기둥 수직철근    
    z0 = -height/2 - footing['cover_upper']
    z1 = -height/2 + footing['cover_lower'] - footing['height']
    xy_distance = 0
    for c, spacing, dia_str in zip(footing_top[0], footing_top[1], footing_top[2]):
        if any(pd.isna(v) for v in (c, spacing, dia_str)):
            break

        lines = []
        dia = footing['ver_dia']
        for _ in range(int(c)):
            xy_distance += spacing
            x0 = center_bottom[0] - footing['length_x']/2 #+ footing['cover_xy']
            y0 = center_bottom[1] - footing['length_y']/2 + xy_distance

            rebar = create_rebar(
                rebar_scale,
                start_point=(x0, y0, z0),
                end_point=(x0, y0, z1),
                r_outer=dia/2
            )
            lines.append(rebar)

        add_rebar('footing_ver', dia, pv.merge(lines))
    
    # 복사    
    for (r_type, dia) in list(rebar_dict.keys()):        
        if r_type != 'footing_ver':            
            continue

        # merge 후 복사
        base_merged = pv.merge(rebar_dict[(r_type, dia)])
        rebar = []
        x_distance = 0
        for c, spacing in zip(footing_top[0], footing_top[1]):
            if any(pd.isna(v) for v in (c, spacing)):
                break
            for _ in range(int(c)):
                x_distance += spacing
                copied = base_merged.copy(deep=True)
                copied.translate((x_distance, 0, 0), inplace=True)
                rebar.append(copied)

        rebar_dict[(r_type, dia)] = [pv.merge(rebar)]

    # 5) 최종 Merge (key별로 [mesh1, mesh2, ...] → 하나로)
    # ----------------------------------------------------
    rebar = {}
    for key, mesh_list in rebar_dict.items():
        rebar[key] = pv.merge(mesh_list)

    return rebar
