import streamlit as st
import numpy as np
import pyvista as pv

def find2_intersection(p1, p2, line_p0, line_dir, tol=1e-6):
    """
    p1, p2: np.array([x, y, z]) (폴리라인 선분 양 끝점)
    line_p0: np.array([x0, y0, z0]) (직선 기준점)
    line_dir: np.array([dx, dy, dz]) (직선 방향 벡터)
    tol: 오차 허용 범위
    반환: 교점 np.array([x, y, z]) 또는 None
    """
    r = p2 - p1
    s = line_dir
    q = line_p0 - p1
    
    cross_rs = np.cross(r, s)
    denom = np.dot(cross_rs, cross_rs)
    
    # 선분과 직선이 평행(또는 거의 평행)인 경우
    if denom < tol:
        return None  # collinear 처리하려면 추가 검사 필요
    
    cross_qs = np.cross(q, s)
    cross_qr = np.cross(q, r)
    
    u = np.dot(cross_qs, cross_rs) / denom
    # t = np.dot(cross_qr, cross_rs) / denom  # 직선 파라미터 (필요 시 사용)
    
    # === 코너 근처 보정(clamp) ===
    if -tol <= u < 0:
        u = 0
    elif 1 < u <= 1+tol:
        u = 1
    
    # u가 [0,1] 범위 내면 선분 위 교차
    if 0 <= u <= 1:
        return p1 + u*r
    return None

def find2_intersection_with_polyline(polyline_points, line_p0, line_dir, tol=1e-6):
    """
    polyline_points: [[x0, y0, z0], [x1, y1, z1], ...]
    line_p0, line_dir: 직선 기준점, 방향벡터
    반환: 교차점 2개 [pt1, pt2] (코너 포함)
    """
    intersections = []
    for i in range(len(polyline_points) - 1):
        p1 = np.array(polyline_points[i])
        p2 = np.array(polyline_points[i+1])
        
        inter_pt = find2_intersection(p1, p2, line_p0, line_dir, tol=tol)
        if inter_pt is not None:
            # 이미 존재하는 교점과 너무 가깝지 않은지 확인 (코너 중복 방지용)
            if not any(np.allclose(inter_pt, ipt, atol=tol) for ipt in intersections):
                intersections.append(inter_pt)
            
            if len(intersections) == 2:
                break
    return intersections


# 호출되는 Function ================================
def find2_point(concrete_data, line_p0, line_dir):

    # 폴리라인(내부 코핑)
    polyline_points = np.array(concrete_data['coping']['xyz_inner'], dtype=np.float32)

    # 교차점 2개 찾기
    intersections = find2_intersection_with_polyline(polyline_points, line_p0, line_dir)

    return intersections


# 호출되는 Function ================================
def create_rebar(rebar_scale, start_point, end_point, r_inner=0, r_outer=25/2):
    """ pv.Disc와 extrude를 사용해 중실원형/중공원형 단면의 Rebar를 생성하는 예시 코드
    r_inner=0 이면 중실원형, r_inner>0 이면 중공원형 모사  """

    r_inner *= rebar_scale
    r_outer *= rebar_scale
    if rebar_scale > 0:
        # 방향 벡터 계산
        direction = np.array(end_point) - np.array(start_point)
        length = np.linalg.norm(direction)
        unit_direction = direction / length

        if r_inner > 0:  # Disc(2D 원판 or 링) 생성            
            disc = pv.Disc(center=start_point, inner=r_inner, outer=r_outer,
                normal=unit_direction,  # - normal : extrude할 방향 벡터
                r_res=10,  # 반경 방향 분할
                c_res=20   # 원주 방향 분할
            )
        else:  # 속도가 월등히 빠름 (중공 모사는 다른 방법으로, 중실만 됨)            
            disc = pv.Polygon(
                center=start_point,       # 중심점
                radius=r_outer,           # 외부 반경 사용 (단일 반경)
                normal=unit_direction,    # 방향 벡터 (extrude 방향)
                n_sides=20                # 원주 방향 분할 수 (Disc의 c_res와 유사)
            )


        # extrude로 disc를 direction만큼 밀어 3D 형상 생성
        # - capping=True 이면 상·하단 면(뚜껑)까지 포함한 표면 메시
        rebar = disc.extrude(vector=direction, capping=True)
        return rebar

    else:
        # rebar_scale <= 0이면 그냥 라인으로 처리
        return pv.Line(start_point, end_point)

