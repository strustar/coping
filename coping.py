import streamlit as st
import pyvista as pv
from copingBasic import set_camera_view, add_arrow_axes, create_volume
from copingData import get_coping_data
from copingRebar import coping_rebar
from stpyvista import stpyvista
import time
import os
import warnings
import platform

# Streamlit 페이지 설정
st.set_page_config(page_title="3D Coping Model", layout="wide")
plotter = pv.Plotter(window_size=[1600, 950], border=False)  # plotter.set_background("black")
# 경고 메시지 무시
warnings.filterwarnings("ignore", category=UserWarning)

# 환경별 설정
if platform.system() == 'Linux':  # Streamlit Cloud 환경
    os.environ["PYVISTA_OFF_SCREEN"] = "true"
    os.environ["PYVISTA_USE_IPYVTK"] = "true"
    os.environ["DISPLAY"] = ":99"
    os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"
    pv.OFF_SCREEN = True
    pv.start_xvfb()
else:  # 로컬 Windows 환경
    pv.OFF_SCREEN = False

# ✅ 상단 여백 제거하는 CSS 적용
st.markdown( """
    <style>
        [data-testid=stSidebar] {
            padding: 5px;
            margin-top: -80px !important;
            background-color: rgba(230, 230, 230, 1);
            border: 3px dashed purple;
            # height: 110% !important;
            # max-width: 600px !important;  /* 사이드바의 최대 크기를 조절합니다 */
            # width: 100% !important;  /* 이렇게 하면 사이드 바 폭을 고정할수 있음. */
        }
        .block-container {
            padding-top: 3rem !important;
        }
    </style> """,
    unsafe_allow_html=True
)

# ✅ 탭 생성
tab1, tab2, tab3, tab4 = st.tabs(["🏗️ 전체 뷰", "🔲 코핑 뷰", "🏛️ 기둥 뷰", "⬛ 기초 뷰"])

start_time = time.time()
with st.sidebar:    
    html_code = """
        <div style="background-color: lightblue; margin-top: 10px; margin-bottom: 10px; padding: 10px; padding-top: 20px; padding-bottom:0px; font-weight:bold; border: 2px solid black; border-radius: 20px;">
            <h5>문의 사항은 아래 이메일로 문의 주세요^^</h5>
            <h5>📧 : <a href='mailto:strustar@konyang.ac.kr' style='color: green; font-size: 16px;'>strustar@konyang.ac.kr</a> (건양대 손병직)</h5>
            <h5>🏠 : <a href='https://sjxtech.kr' style='color: green; font-size: 16px;'>sjxtech.kr</a> (SJ Tech 홈페이지)</h5>
        </div>
    """
    st.markdown(html_code, unsafe_allow_html=True)
    # st.title("3D Coping Model")

    # 파일 다운로드 & 업로드 버튼 생성
    col = st.columns([1, 1])
    with col[0]:
        with st.expander(":green[Input 파일 다운로드 & 업로드]"):
            with open("coping_input.xlsx", "rb") as f:
                file_data = f.read()
            st.download_button(
                label="Input 엑셀 파일 다운로드",
                data=file_data,
                file_name="coping_input.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            uploaded_file = st.file_uploader("Upload Excel file", type=['xlsx'])
    with col[1]:
        with st.expander(":green[카메라 위치 (iso, top 뷰 등)]"):
            camera_position = st.radio(":orange[카메라 위치]", ["iso", "Top", "Bottom", "Front", 'Back', 'Right', 'Left'], index=0)

    col = st.columns([1.5, 1])
    with col[0]:
        camera_projection = st.radio(":orange[카메라 투영*]", ["orthographic", "perspective"], horizontal=True, index=1)
    with col[1]:
        model_symmetry = st.checkbox(":orange[전체 모델 (대칭)]", value=False)
    st.write('###### :blue[*도면은 orthographic(직교 뷰)로 봐야 하지만, 현재 웹 표시는 원근 뷰만 지원 (다소 찌글어 보일수 있음)]')
    st.write('###### :blue[**조만간 orthographic(직교 뷰)도 지원될 것으로 보임]')
    
    col = st.columns(2)
    with col[0]:
        rebar_scale = st.number_input(":orange[Rebar Scale*]", min_value=0., value=1., step=1., format="%.f")
    with col[1]:
        pass
    st.write('###### :blue[*0이면 선만 표시, 1이면 실제 직경, 2이면 2배 크게 표시 등]')

    col = st.columns(2)
    with col[0]:
        rebar_opacity = st.number_input(":orange[Rebar Opacity]", min_value=0., value=1., step=0.1, max_value=1., format="%.1f")
    with col[1]:
        rebar_line_width = st.number_input(":orange[Rebar Line Width]", min_value=1., value=2., step=1., format="%.f")    

    # st.write('###### :orange[Concrete]')
    col = st.columns(2)    
    with col[0]:
        volume_opacity = st.number_input(":orange[Volume Opacity]", min_value=0., value=0.3, step=0.1, format="%.1f")
    with col[1]:
        volume_line_width = st.number_input(":orange[Volume Line Width]", min_value=1., value=3., step=1., format="%.f")

concrete_data = get_coping_data(uploaded_file)
length = concrete_data['length']
column = concrete_data['column']

coping_cover = concrete_data['coping_cover']['thickness']
inner_points = concrete_data['coping']['xyz_inner']
outer_points = concrete_data['coping']['xyz']
column_rebar = concrete_data['column_rebar']
footing = concrete_data['footing']

color_map = {'coping_outer': 'red', 'coping_x': 'magenta', 'coping_z': 'green', 'coping_y': 'blue',
    'column_tie': 'purple', 'column_rebar': 'cyan', 'column_cross': 'red',
    'footing_top': 'green', 'footing_bottom': 'orange', 'footing_ver': 'purple'}

volumes, lines = create_volume(concrete_data)
rebar = coping_rebar(rebar_scale, concrete_data)

# ✅ 중복 없는 리바 타입 & 직경 목록 생성 후 'All' 추가
unique_types = ["All"] + sorted(set(r_type for r_type, _ in rebar))
unique_dias = ['All'] + sorted(list(set(int(dia) for _, dia in rebar)))

with st.sidebar:
    col = st.columns(2)
    with col[0]:
        rebar_type = st.radio(":orange[철근 타입]", options=unique_types)
    with col[1]:
        rebar_dia = st.radio(":orange[철근 직경]", options=unique_dias)

volume_color, line_color = 'gray', 'blue'
def common_plot(num):
    if num == 100:        
        plotter.add_mesh(volumes.combine(), color=volume_color, opacity=volume_opacity)
        plotter.add_mesh(lines.combine(), color=line_color, opacity=volume_opacity, line_width=volume_line_width)
    else:
        plotter.add_mesh(volumes[num], color=volume_color, opacity=volume_opacity)
        plotter.add_mesh(lines[num], color=line_color, opacity=volume_opacity, line_width=volume_line_width)

    add_arrow_axes(plotter)
    set_camera_view(plotter, camera_projection, camera_position)
    stpyvista(plotter)


with tab1:  # 전체 뷰
    for (r_type, dia) in rebar:
        # ✅ 선택된 타입과 직경에 맞게 필터링
        if ((rebar_type == "All" or r_type == rebar_type) and
            (rebar_dia == "All" or int(dia) == int(rebar_dia))):

            mesh = rebar[(r_type, dia)]
            color = color_map.get(r_type, 'green')
            plotter.add_mesh(
                mesh,
                color=color,
                line_width=rebar_line_width,
                opacity=rebar_opacity,
            )
    if model_symmetry:
        volumes_mesh = volumes.combine()
        mirrored_mesh = volumes_mesh.reflect((1, 0, 0))  # X축 기준 반사
        lines_mesh = lines.combine()
        mirrored_lines = lines_mesh.reflect((1, 0, 0))  # X축 기준 반사

        plotter.add_mesh(mirrored_mesh, color=volume_color, opacity=volume_opacity)
        plotter.add_mesh(mirrored_lines, color=line_color, opacity=volume_opacity, line_width=volume_line_width)
    common_plot(100)


with tab2:  # 코핑 뷰
    plotter.clear()

    for (r_type, dia) in rebar:
        if ('coping' in r_type) and \
            (rebar_type == "All" or r_type == rebar_type) and \
            (rebar_dia == "All" or int(dia) == int(rebar_dia)):

            mesh = rebar[(r_type, dia)]
            color = color_map.get(r_type, 'green')
            plotter.add_mesh(
                mesh,
                color=color,
                line_width=rebar_line_width,
                opacity=rebar_opacity,
            )
    common_plot(0)

with tab3:  # 기둥 뷰
    plotter.clear()

    for (r_type, dia) in rebar:
        if ('column' in r_type) and \
            (rebar_type == "All" or r_type == rebar_type) and \
            (rebar_dia == "All" or int(dia) == int(rebar_dia)):

            mesh = rebar[(r_type, dia)]
            color = color_map.get(r_type, 'green')
            plotter.add_mesh(
                mesh,
                color=color,
                line_width=rebar_line_width,
                opacity=rebar_opacity,
            )
    common_plot(1)

with tab4:  # 기초 뷰
    plotter.clear()

    for (r_type, dia) in rebar:
        if ('footing' in r_type) and \
            (rebar_type == "All" or r_type == rebar_type) and \
            (rebar_dia == "All" or int(dia) == int(rebar_dia)):

            mesh = rebar[(r_type, dia)]
            color = color_map.get(r_type, 'green')
            plotter.add_mesh(
                mesh,
                color=color,
                line_width=rebar_line_width,
                opacity=rebar_opacity,
            )
    common_plot(2)



end_time = time.time()
execution_time = end_time - start_time
# st.sidebar.write('---')
st.sidebar.write(f"실행 시간: {execution_time:.4f} 초")



