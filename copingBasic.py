import numpy as np
import pyvista as pv
import streamlit as st

def get_all_bounds(plotter):
    x_min, x_max = float('inf'), float('-inf')
    y_min, y_max = float('inf'), float('-inf')
    z_min, z_max = float('inf'), float('-inf')
    
    for actor in plotter.actors.values():
        mesh = actor.GetMapper().GetInput()
        if mesh:
            bounds = mesh.GetBounds()   # bounds = [x_min, x_max, y_min, y_max, z_min, z_max]            
            x_min = min(x_min, bounds[0])
            x_max = max(x_max, bounds[1])
            y_min = min(y_min, bounds[2])
            y_max = max(y_max, bounds[3])
            z_min = min(z_min, bounds[4])
            z_max = max(z_max, bounds[5])
    
    return {
        'x': (x_min, x_max),
        'y': (y_min, y_max),
        'z': (z_min, z_max)
    }

def add_arrow_axes(plotter, opacity=0.4, scale=2000):
    bounds = get_all_bounds(plotter)
    z0 = np.mean(bounds['z'])   # z0 = 0

    plotter.add_box_axes()  # xyz 축 표시 (이것이 스트림릿 웹에 표시 안됨 ㅠㅠ)
    x_arrow = pv.Arrow(direction=(1, 0, 0), scale=scale)
    y_arrow = pv.Arrow(direction=(0, 1, 0), scale=scale)
    z_arrow = pv.Arrow(direction=(0, 0, 1), scale=scale)

    x_arrow_copy = x_arrow.copy(deep=True)  # deep copy 생성
    x_arrow_copy.translate((0, 0, z0), inplace=True)  # 새로운 위치로 이동
    y_arrow_copy = y_arrow.copy(deep=True)
    y_arrow_copy.translate((0, 0, z0), inplace=True)
    z_arrow_copy = z_arrow.copy(deep=True)
    z_arrow_copy.translate((0, 0, z0), inplace=True)
    plotter.add_mesh(x_arrow_copy, color="red", opacity=opacity)
    plotter.add_mesh(y_arrow_copy, color="green", opacity=opacity)
    plotter.add_mesh(z_arrow_copy, color="blue", opacity=opacity)
    return plotter

def set_camera_view(plotter, camera_projection, camera_position):
    if camera_projection == "orthographic":
        plotter.enable_parallel_projection()
        # plotter.camera.parallel_scale = 80        # 직교 뷰 크기 조정
    else:
        plotter.disable_parallel_projection()
        # plotter.camera.view_angle = 45            # 원근 시야각 조정

    # 각 뷰 타입별 카메라 위치 정의
    scale = 1
    view_positions = {
        "iso": (-scale, -scale, scale),
        "Top": (0, 0, scale),
        "Bottom": (0, 0, -scale),
        "Left": (-scale, 0, 0),
        "Right": (scale, 0, 0),
        "Front": (0, -scale, 0),
        "Back": (0, scale, 0)
    }
        
    plotter.camera.position = view_positions.get(camera_position)
    plotter.camera.focal_point = (0, 0, 0)  # 원점을 바라보도록 설정
    
    # Top/Bottom 뷰의 경우 up 벡터 조정
    if camera_position in ["Top", "Bottom"]:
        plotter.camera.up = (0.0, 1.0, 0.0)
    else:
        plotter.camera.up = (0.0, 0.0, 1.0)
    plotter.reset_camera()  # fit view    # plotter.camera.zoom(1.0)

    return plotter


def create_volume(concrete_data):
    polyline_points = concrete_data['coping']['xyz'].astype(np.float32)
    outer_points = concrete_data['coping']['xyz']
    footing = concrete_data['footing']

    length = concrete_data['length']
    column = concrete_data['column']

    # ----------------------------------------------------
    # 1) coping volume
    # ----------------------------------------------------
    # PolyData 생성 및 면(Faces) 정보 설정
    surface = pv.PolyData(polyline_points)
    surface.faces = np.hstack([len(polyline_points), np.arange(len(polyline_points))])

    # extrude로 두께(또는 길이) 확장
    y0 = concrete_data['length']['y']
    coping_volume = surface.extrude([0, y0, 0], capping=True)
    lines = coping_volume.extract_feature_edges(boundary_edges=True, non_manifold_edges=True, feature_edges=True, manifold_edges=True)   # 외곽선 추출

    lines1 = []
    for idx in range(len(polyline_points)):
        if idx < len(polyline_points):
            p1 = polyline_points[idx] #.copy()
            p2 = p1.copy()            
            p2[1] += y0  # y좌표를 y0만큼 이동
            lines1.append(pv.Line(p1, p2))
    coping_lines = pv.merge([lines, *lines1])

    # ----------------------------------------------------
    # 2) column volume
    # ----------------------------------------------------
    xc = (outer_points[2][0] + outer_points[3][0]) / 2
    column_center = (xc, length['y']/2, 0)
    column_volume = pv.Cylinder(center=column_center, direction=(0, 0, 1), radius=column['diameter']/2, height=column['height'], resolution=50)
    column_lines = column_volume.extract_feature_edges()  # 외곽선만 추출

    # ----------------------------------------------------
    # 3) footing volume
    # ----------------------------------------------------
    footing_volume = pv.Cube(center=(xc, length['y']/2, -column['height']/2 - footing['height']/2),
            x_length=footing['length_x'], y_length=footing['length_y'], z_length=footing['height'])
    footing_lines = footing_volume.extract_feature_edges()

    volumes = pv.MultiBlock()
    lines = pv.MultiBlock()
    volumes["Coping Volume"] = coping_volume
    volumes["Column Volume"] = column_volume
    volumes["Footing Volume"] = footing_volume
    lines["Coping Lines"] = coping_lines
    lines["Column Lines"] = column_lines
    lines["Footing Lines"] = footing_lines

    return volumes, lines

