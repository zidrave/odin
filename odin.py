#version mejorada 1.0
import curses
import sys
import os
import time
import termios

def guardar_archivo(lineas, nombre):
    with open(nombre, 'w') as f:
        for linea in lineas:
            f.write(linea + '\n')

def pedir_nombre_archivo(stdscr):
    curses.echo()
    prompt = "filename to save: "
    prompt_x = len(prompt)
    stdscr.addstr(curses.LINES - 1, 0, prompt)
    stdscr.clrtoeol()
    nombre = ''
    pos = 0
    while True:
        key = stdscr.getch()
        if key in (10, 13):
            break
        elif key in (8, 127, curses.KEY_BACKSPACE):
            if pos > 0:
                nombre = nombre[:pos-1] + nombre[pos:]
                pos -= 1
        elif key == curses.KEY_LEFT:
            if pos > 0:
                pos -= 1
        elif key == curses.KEY_RIGHT:
            if pos < len(nombre):
                pos += 1
        elif key == curses.KEY_HOME:
            pos = 0
        elif key == curses.KEY_END:
            pos = len(nombre)
        elif 32 <= key <= 126:
            nombre = nombre[:pos] + chr(key) + nombre[pos:]
            pos += 1

        maxw = curses.COLS - prompt_x - 1
        start = max(0, pos - maxw + 1)
        visible = nombre[start:start + maxw]

        stdscr.addstr(curses.LINES - 1, prompt_x, ' ' * maxw)
        stdscr.addstr(curses.LINES - 1, prompt_x, visible)
        stdscr.move(curses.LINES - 1, prompt_x + min(pos - start, maxw - 1))

    curses.noecho()
    return nombre

def editor(stdscr, archivo_inicial=None):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_RED)
    curses.init_pair(6, curses.COLOR_BLUE, -1)

    curses.curs_set(1)
    stdscr.keypad(True)

    archivo = archivo_inicial
    lineas = ['']
    modo_comando = False
    comando = ''
    cursor_x, cursor_y = 0, 0
    offset_y = 0
    scroll_x = 0
    modo_insertar = True
    mostrar_lineas = True

    mostrar_mensaje = ''
    mostrar_mensaje_color = 0
    mostrar_mensaje_tiempo = 0

    seleccionando = False
    sel_inicio = None
    sel_fin = None
    portapapeles = ''

    if archivo and os.path.exists(archivo):
        with open(archivo, 'r') as f:
            lineas = f.read().splitlines()
    else:
        lineas = ['']

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        titulo = archivo if archivo else "[Sin nombre]"
        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(0, 0, " " * (w - 1))
        stdscr.attroff(curses.color_pair(1))
        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(0, (w - len(titulo.strip())) // 2, titulo.strip())
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)

        for idx in range(offset_y, offset_y + h - 2):
            if idx >= len(lineas):
                break
            linea = lineas[idx]
            line_start_x = 0
            if mostrar_lineas:
                stdscr.attron(curses.color_pair(2))
                stdscr.addstr(idx - offset_y + 1, 0, f"{idx + 1:>3} ")
                stdscr.attroff(curses.color_pair(2))
                line_start_x = 4

            visible_line = linea[scroll_x:scroll_x + (w - line_start_x - 1)]

            if seleccionando and sel_inicio and sel_fin:
                sy, sx = sel_inicio
                ey, ex = sel_fin
                if (sy, sx) > (ey, ex):
                    sy, sx, ey, ex = ey, ex, sy, sx
                if sy <= idx <= ey:
                    inicio = 0
                    fin = len(visible_line)
                    if idx == sy:
                        inicio = max(0, sx - scroll_x)
                    if idx == ey:
                        fin = min(len(visible_line), ex - scroll_x)
                    stdscr.addstr(idx - offset_y + 1, line_start_x, visible_line[:inicio])
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addstr(idx - offset_y + 1, line_start_x + inicio, visible_line[inicio:fin])
                    stdscr.attroff(curses.A_REVERSE)
                    stdscr.addstr(idx - offset_y + 1, line_start_x + fin, visible_line[fin:])
                else:
                    stdscr.addstr(idx - offset_y + 1, line_start_x, visible_line)
            else:
                stdscr.addstr(idx - offset_y + 1, line_start_x, visible_line)

        if cursor_x < scroll_x:
            scroll_x = cursor_x
        elif cursor_x >= scroll_x + (w - (4 if mostrar_lineas else 0) - 1):
            scroll_x = cursor_x - (w - (4 if mostrar_lineas else 0) - 2)

        if cursor_y < offset_y:
            offset_y = cursor_y
        elif cursor_y >= offset_y + h - 2:
            offset_y = cursor_y - (h - 3)

        if mostrar_mensaje and time.time() - mostrar_mensaje_tiempo < 1.5:
            stdscr.attron(mostrar_mensaje_color)
            stdscr.addstr(h - 1, 0, mostrar_mensaje[:w - 1])
            stdscr.clrtoeol()
            stdscr.attroff(mostrar_mensaje_color)
        elif modo_comando:
            stdscr.attron(curses.color_pair(3))
            stdscr.addstr(h - 1, 0, f":{comando}"[:w - 1])
            stdscr.clrtoeol()
            stdscr.attroff(curses.color_pair(3))
        else:
            if offset_y <= cursor_y < offset_y + h - 2:
                cursor_offset = 4 if mostrar_lineas else 0
                stdscr.move(cursor_y - offset_y + 1, cursor_x - scroll_x + cursor_offset)

        stdscr.refresh()
        key = stdscr.getch()

        if seleccionando:
            sel_fin = (cursor_y, cursor_x)

        if key == 27:
            stdscr.nodelay(True)
            siguiente = stdscr.getch()
            stdscr.nodelay(False)
            if siguiente == -1 or siguiente == ord('e'):
                modo_comando = not modo_comando
                comando = ''
                continue
            elif siguiente == ord('m'):
                if not seleccionando:
                    sel_inicio = (cursor_y, cursor_x)
                    sel_fin = (cursor_y, cursor_x)
                    seleccionando = True
                else:
                    seleccionando = False
                continue
            elif siguiente == ord('s'):
                if not archivo:
                    archivo = pedir_nombre_archivo(stdscr)
                guardar_archivo(lineas, archivo)
                mostrar_mensaje = f"Archivo guardado en {archivo}"
                mostrar_mensaje_color = curses.color_pair(6)
                mostrar_mensaje_tiempo = time.time()
                continue
            elif siguiente == ord('q'):
                break
            elif siguiente == ord('c'):
                if seleccionando and sel_inicio and sel_fin:
                    sy, sx = sel_inicio
                    ey, ex = sel_fin
                    if (sy, sx) > (ey, ex):
                        sy, sx, ey, ex = ey, ex, sy, sx
                    if sy == ey:
                        portapapeles = lineas[sy][sx:ex]
                    else:
                        portapapeles = '\n'.join([
                            lineas[sy][sx:]
                        ] + lineas[sy + 1:ey] + [lineas[ey][:ex]])
                    mostrar_mensaje = "Texto copiado"
                    mostrar_mensaje_color = curses.color_pair(6)
                    mostrar_mensaje_tiempo = time.time()
                continue
            elif siguiente == ord('x'):
                if seleccionando and sel_inicio and sel_fin:
                    sy, sx = sel_inicio
                    ey, ex = sel_fin
                    if (sy, sx) > (ey, ex):
                        sy, sx, ey, ex = ey, ex, sy, sx
                    if sy == ey:
                        portapapeles = lineas[sy][sx:ex]
                        lineas[sy] = lineas[sy][:sx] + lineas[sy][ex:]
                    else:
                        portapapeles = '\n'.join([
                            lineas[sy][sx:]
                        ] + lineas[sy + 1:ey] + [lineas[ey][:ex]])
                        lineas[sy] = lineas[sy][:sx] + lineas[ey][ex:]
                        del lineas[sy + 1:ey + 1]
                    seleccionando = False
                    mostrar_mensaje = "Texto cortado"
                    mostrar_mensaje_color = curses.color_pair(6)
                    mostrar_mensaje_tiempo = time.time()
                continue
            elif siguiente == ord('v'):
                if portapapeles:
                    partes = portapapeles.split('\n')
                    if len(partes) == 1:
                        lineas[cursor_y] = lineas[cursor_y][:cursor_x] + partes[0] + lineas[cursor_y][cursor_x:]
                        cursor_x += len(partes[0])
                    else:
                        inicio = lineas[cursor_y][:cursor_x] + partes[0]
                        fin = partes[-1] + lineas[cursor_y][cursor_x:]
                        lineas[cursor_y] = inicio
                        for i in range(1, len(partes) - 1):
                            lineas.insert(cursor_y + i, partes[i])
                        lineas.insert(cursor_y + len(partes) - 1, fin)
                        cursor_y += len(partes) - 1
                        cursor_x = len(partes[-1])
                    mostrar_mensaje = "Texto pegado"
                    mostrar_mensaje_color = curses.color_pair(6)
                    mostrar_mensaje_tiempo = time.time()
                continue

        if modo_comando:
            if key in (10, 13):
                comando_input = comando.strip()
                if comando_input == 'q':
                    break
                elif comando_input == 'l':
                    mostrar_lineas = not mostrar_lineas
                elif comando_input == 'w':
                    nombre_guardar = archivo or pedir_nombre_archivo(stdscr)
                    guardar_archivo(lineas, nombre_guardar)
                    archivo = nombre_guardar
                    mostrar_mensaje = f"Archivo guardado en {archivo}"
                    mostrar_mensaje_color = curses.color_pair(6)
                    mostrar_mensaje_tiempo = time.time()
                elif comando_input == 'wq':
                    nombre_guardar = archivo or pedir_nombre_archivo(stdscr)
                    guardar_archivo(lineas, nombre_guardar)
                    archivo = nombre_guardar
                    break
                elif comando_input.startswith('wf:'):
                    nuevo_nombre = comando_input[3:].strip()
                    if nuevo_nombre:
                        guardar_archivo(lineas, nuevo_nombre)
                        mostrar_mensaje = f"Copia guardada como {nuevo_nombre}"
                        mostrar_mensaje_color = curses.color_pair(6)
                        mostrar_mensaje_tiempo = time.time()
                comando = ''
                modo_comando = False
            elif key in (8, 127, curses.KEY_BACKSPACE):
                comando = comando[:-1]
            elif 32 <= key <= 126:
                comando += chr(key)
        else:
            if key == curses.KEY_UP:
                if cursor_y > 0:
                    cursor_y -= 1
                    cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_DOWN:
                if cursor_y < len(lineas) - 1:
                    cursor_y += 1
                    cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_LEFT:
                if cursor_x > 0:
                    cursor_x -= 1
            elif key == curses.KEY_RIGHT:
                if cursor_x < len(lineas[cursor_y]):
                    cursor_x += 1
            elif key == 10:
                nueva = lineas[cursor_y][cursor_x:]
                lineas[cursor_y] = lineas[cursor_y][:cursor_x]
                lineas.insert(cursor_y + 1, nueva)
                cursor_y += 1
                cursor_x = 0
            elif key in (127, curses.KEY_BACKSPACE):
                if cursor_x > 0:
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x - 1] + lineas[cursor_y][cursor_x:]
                    cursor_x -= 1
                elif cursor_y > 0:
                    prev_len = len(lineas[cursor_y - 1])
                    lineas[cursor_y - 1] += lineas[cursor_y]
                    del lineas[cursor_y]
                    cursor_y -= 1
                    cursor_x = prev_len
            elif 32 <= key <= 126:
                lineas[cursor_y] = lineas[cursor_y][:cursor_x] + chr(key) + lineas[cursor_y][cursor_x:]
                cursor_x += 1

def main():
    os.environ.setdefault('ESCDELAY', '25')
    fd = sys.stdin.fileno()
    attrs = termios.tcgetattr(fd)
    attrs[3] = attrs[3] & ~termios.IXON
    termios.tcsetattr(fd, termios.TCSANOW, attrs)

    archivo = sys.argv[1] if len(sys.argv) > 1 else None
    curses.wrapper(editor, archivo)

if __name__ == "__main__":
    main()
#eof
