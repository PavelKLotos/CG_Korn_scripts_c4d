import c4d
from c4d import gui

# Константы
RESET_TRANSFORM_CMD_ID = 1019940
PANZOOM_CAM_NAME = "PanZoomCam"
PANZOOM_LOCK_NAME = "PanZoomLock"
TWOD_PANZOOM_NAME = "2DPanZoom"
PURPLE_COLOR = c4d.Vector(147/255.0, 88/255.0, 178/255.0)  # #9358B2
DEFAULT_COLOR = c4d.Vector(0.0, 0.0, 0.0)                  # #000000
REDSHIFT_CAMERA_TYPE = 1057516
RECTANGLE_SELECTION_CMD_ID = 200000084
MOTION_TRACKER_CREATE_CMD = 1036374

# Запоминаем рендер-движок (это важно для повторных запусков)
current_render_engine = None

def find_child_by_name(obj, name):
    """Рекурсивный поиск дочернего объекта по имени"""
    child = obj.GetDown()
    while child:
        if child.GetName() == name:
            return child
        nested = find_child_by_name(child, name)
        if nested:
            return nested
        child = child.GetNext()
    return None

def remove_animation_tracks(obj, doc):
    """Удаляет анимационные треки позиции, вращения и масштаба"""
    track_ids = [
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION), c4d.DescLevel(c4d.VECTOR_X)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION), c4d.DescLevel(c4d.VECTOR_Y)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_POSITION), c4d.DescLevel(c4d.VECTOR_Z)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION), c4d.DescLevel(c4d.VECTOR_X)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION), c4d.DescLevel(c4d.VECTOR_Y)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_ROTATION), c4d.DescLevel(c4d.VECTOR_Z)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_SCALE), c4d.DescLevel(c4d.VECTOR_X)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_SCALE), c4d.DescLevel(c4d.VECTOR_Y)),
        c4d.DescID(c4d.DescLevel(c4d.ID_BASEOBJECT_REL_SCALE), c4d.DescLevel(c4d.VECTOR_Z))
    ]
    tracks = obj.GetCTracks()
    for track in tracks[:]:
        if track and track.GetDescriptionID() in track_ids:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, track)
            track.Remove()

def clear_object_children_and_tags(obj, doc):
    """Удаляет ВСЕ дочерние объекты и ВСЕ теги (включая Protection Tag)"""
    # Удаляем все теги
    for tag in obj.GetTags()[:]:
        doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
        tag.Remove()

    # Удаляем всех детей рекурсивно
    child = obj.GetDown()
    while child:
        next_child = child.GetNext()
        doc.AddUndo(c4d.UNDOTYPE_DELETE, child)
        child.Remove()
        child = next_child

def switch_render_engine_to_standard():
    """Переключаем движок рендеринга на стандартный и восстанавливаем после выполнения всех действий"""
    doc = c4d.documents.GetActiveDocument()
    if not doc:
        print("Не удалось получить документ")
        return

    # Получаем настройки рендеринга
    render_data = doc.GetActiveRenderData()
    if not render_data:
        print("Не удалось получить настройки рендеринга")
        return

    # Получаем текущий движок рендеринга
    current_render_engine = render_data[c4d.RDATA_RENDERENGINE]
    print(f"Текущий движок рендеринга: {current_render_engine}")

    # Проверяем, если движок уже стандартный, не переключаем
    if current_render_engine != 0:
        try:
            print("Переключаем на стандартный рендер...")
            render_data[c4d.RDATA_RENDERENGINE] = 0  # Стандартный рендер (идентификатор = 0)
            c4d.EventAdd()  # Обновляем интерфейс
            print(f"Движок рендеринга изменен на стандартный.")
        except Exception as e:
            print(f"Ошибка при изменении движка рендеринга на стандартный: {e}")
        else:
            render_data = doc.GetActiveRenderData()
            print(f"После изменения движок рендеринга: {render_data[c4d.RDATA_RENDERENGINE]}")

    return current_render_engine  # Возвращаем текущий движок для восстановления

def main():
    global current_render_engine

    doc = c4d.documents.GetActiveDocument()
    if not doc:
        gui.MessageDialog("Не удалось получить документ")
        return

    bd = doc.GetActiveBaseDraw()
    if not bd:
        gui.MessageDialog("Не удалось получить активный видовой порт")
        return

    active_cam = bd.GetSceneCamera(doc)
    if not active_cam:
        active_cam = doc.SearchObjectType(c4d.Ocamera)
        if not active_cam:
            gui.MessageDialog("В сцене нет камеры!")
            return

    is_redshift = active_cam.GetType() == REDSHIFT_CAMERA_TYPE

    # Проверяем, был ли уже сделан первый запуск и нужно ли переключать рендер
    if current_render_engine is None:
        # Переключаем движок рендеринга на стандартный перед созданием Motion Tracker
        current_render_engine = switch_render_engine_to_standard()

    # ────────────── ПОВТОРНЫЙ ЗАПУСК / ВЫКЛЮЧЕНИЕ ──────────────
    current_cam = bd.GetSceneCamera(doc)
    is_special = current_cam.GetName() in [PANZOOM_CAM_NAME, PANZOOM_LOCK_NAME, TWOD_PANZOOM_NAME]
    has_panzoom = find_child_by_name(current_cam, PANZOOM_CAM_NAME) or \
                  find_child_by_name(current_cam, PANZOOM_LOCK_NAME) or \
                  find_child_by_name(current_cam, TWOD_PANZOOM_NAME)

    if is_special or has_panzoom:
        parent_cam = current_cam
        while parent_cam:
            if find_child_by_name(parent_cam, TWOD_PANZOOM_NAME):
                break
            parent_cam = parent_cam.GetUp()

        if not parent_cam:
            gui.MessageDialog("Не удалось найти родительскую камеру")
            return

        doc.StartUndo()

        bd.SetSceneCamera(parent_cam)
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)
        c4d.EventAdd()

        bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = DEFAULT_COLOR
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)

        for name in [PANZOOM_CAM_NAME, PANZOOM_LOCK_NAME, TWOD_PANZOOM_NAME]:
            obj = find_child_by_name(parent_cam, name)
            if obj:
                doc.AddUndo(c4d.UNDOTYPE_DELETE, obj)
                obj.Remove()

        parent_cam[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_UNDEF
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, parent_cam)

        c4d.CallCommand(RECTANGLE_SELECTION_CMD_ID)

        print("Вернулись к родительской камере, удалили PanZoomCam, PanZoomLock и 2DPanZoom")
        doc.EndUndo()
        c4d.EventAdd()
        
        # Восстанавливаем рендер-движок, не переключаем на стандартный
        doc.GetActiveRenderData()[c4d.RDATA_RENDERENGINE] = current_render_engine
        c4d.EventAdd()
        
        return

    # ────────────── ПЕРВЫЙ ЗАПУСК ──────────────
    doc.StartUndo()

    # 1. Создаём PanZoomLock (клон активной камеры)
    panzoom_lock = active_cam.GetClone()
    if not panzoom_lock:
        gui.MessageDialog("Не удалось клонировать камеру для PanZoomLock")
        doc.EndUndo()
        return

    # Чистим клон: все дети + все теги
    clear_object_children_and_tags(panzoom_lock, doc)

    remove_animation_tracks(panzoom_lock, doc)

    panzoom_lock.SetName(PANZOOM_LOCK_NAME)

    # Вставляем как дочерний под активную камеру
    panzoom_lock.InsertUnder(active_cam)

    # Выполняем сброс PSR вручную
    panzoom_lock.SetAbsPos(c4d.Vector(0.0, 0.0, 0.0))  # Сбрасываем позицию
    panzoom_lock.SetAbsRot(c4d.Vector(0.0, 0.0, 0.0))  # Сбрасываем вращение
    panzoom_lock.SetAbsScale(c4d.Vector(1.0, 1.0, 1.0))  # Сбрасываем масштаб

    # ДОБАВЛЯЕМ Protection Tag НА PanZoomLock ТОЛЬКО ПОСЛЕ ВСТАВКИ В ИЕРАРХИЮ
    protection_tag = c4d.BaseTag(c4d.Tprotection)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, protection_tag)
    panzoom_lock.InsertTag(protection_tag)
    print("Protection Tag добавлен на PanZoomLock после вставки в иерархию")

    # 2. Создаём Motion Tracker через команду меню
    doc.SetActiveObject(active_cam)
    c4d.CallCommand(MOTION_TRACKER_CREATE_CMD)

    mt = None
    for obj in doc.GetObjects():
        if obj.GetType() == c4d.Omotiontracker:
            mt = obj
            break

    if not mt:
        gui.MessageDialog("Не удалось найти созданный Motion Tracker")
        doc.EndUndo()
        return

    solved_cam = mt.GetDown()
    if not solved_cam or solved_cam.GetType() not in [c4d.Ocamera, REDSHIFT_CAMERA_TYPE]:
        gui.MessageDialog("Не найдена дочерняя камера в Motion Tracker")
        doc.EndUndo()
        return

    for tag in solved_cam.GetTags()[:]:
        if tag.GetType() == c4d.Tprotection:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, tag)
            tag.Remove()

    doc.AddUndo(c4d.UNDOTYPE_CHANGE, solved_cam)
    solved_cam[c4d.CAMERA_FOCUS] = active_cam[c4d.CAMERA_FOCUS]
    if is_redshift:
        solved_cam[c4d.RSCAMERAOBJECT_SENSOR_SHIFT] = active_cam[c4d.RSCAMERAOBJECT_SENSOR_SHIFT]
    else:
        solved_cam[c4d.CAMERAOBJECT_FILM_OFFSET_X] = active_cam[c4d.CAMERAOBJECT_FILM_OFFSET_X]
        solved_cam[c4d.CAMERAOBJECT_FILM_OFFSET_Y] = active_cam[c4d.CAMERAOBJECT_FILM_OFFSET_Y]

    mt.InsertUnder(active_cam)
    solved_cam.InsertTag(c4d.BaseTag(c4d.Tprotection))

    mt.SetName(TWOD_PANZOOM_NAME)
    solved_cam.SetName(PANZOOM_CAM_NAME)

    solved_cam[c4d.ID_BASEOBJECT_COLOR] = PURPLE_COLOR
    bd[c4d.BASEDRAW_DATA_TINTBORDER_COLOR] = PURPLE_COLOR

    active_cam[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF
    solved_cam[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF
    panzoom_lock[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF
    mt[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.OBJECT_OFF

    bd.SetSceneCamera(solved_cam)
    doc.AddUndo(c4d.UNDOTYPE_CHANGE, bd)

    mt[c4d.PH_SOLVE_MODE] = c4d.PH_SOLVE_MODE_NODAL

    doc.SetActiveObject(mt)
    doc.EndUndo()
    c4d.EventAdd()

    print("Скрипт выполнен: PanZoomLock с Protection Tag (добавлен после вставки в иерархию) → Motion Tracker → PanZoomCam активна")

    # Восстанавливаем движок рендеринга на исходный
    doc.GetActiveRenderData()[c4d.RDATA_RENDERENGINE] = current_render_engine
    c4d.EventAdd()

if __name__ == "__main__":
    main()
