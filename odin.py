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
    stdscr.addstr(curses.LINES - 1, 0, "Nombre del archivo para guardar: ")
    stdscr.clrtoeol()
    nombre = stdscr.getstr().decode()
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

            if seleccionando and sel_inicio and sel_fin:
                sy, sx = sel_inicio
                ey, ex = sel_fin
                if (sy, sx) > (ey, ex):
                    sy, sx, ey, ex = ey, ex, sy, sx
                if sy <= idx <= ey:
                    inicio = 0
                    fin = len(linea)
                    if idx == sy:
                        inicio = sx
                    if idx == ey:
                        fin = ex
                    inicio = max(0, min(len(linea), inicio))
                    fin = max(0, min(len(linea), fin))
                    stdscr.addstr(idx - offset_y + 1, line_start_x, linea[:inicio])
                    stdscr.attron(curses.A_REVERSE)
                    stdscr.addstr(idx - offset_y + 1, line_start_x + inicio, linea[inicio:fin])
                    stdscr.attroff(curses.A_REVERSE)
                    stdscr.addstr(idx - offset_y + 1, line_start_x + fin, linea[fin:])
                else:
                    stdscr.addstr(idx - offset_y + 1, line_start_x, linea)
            else:
                stdscr.addstr(idx - offset_y + 1, line_start_x, linea)

        if mostrar_mensaje and time.time() - mostrar_mensaje_tiempo < 1.5:
            stdscr.attron(mostrar_mensaje_color)
            stdscr.addstr(h - 1, 0, mostrar_mensaje)
            stdscr.clrtoeol()
            stdscr.attroff(mostrar_mensaje_color)
        elif modo_comando:
            stdscr.attron(curses.color_pair(3))
            stdscr.addstr(h - 1, 0, f":{comando}")
            stdscr.clrtoeol()
            stdscr.attroff(curses.color_pair(3))
        else:
            if offset_y <= cursor_y < offset_y + h - 2:
                cursor_offset = 4 if mostrar_lineas else 0
                stdscr.move(cursor_y - offset_y + 1, cursor_x + cursor_offset)

        stdscr.refresh()

        key = stdscr.getch()

        if key == 27:
            stdscr.nodelay(True)
            siguiente = stdscr.getch()
            stdscr.nodelay(False)

            if siguiente == -1:
                if modo_comando:
                    comando = ''
                    modo_comando = False
                else:
                    modo_comando = True
                    comando = ''
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
            else:
                key = siguiente

        if modo_comando:
            if key in (10, 13):
                comando_input = comando.strip()
                if comando_input in ('q', 'q!'):
                    break
                elif comando_input == 'wq':
                    if not archivo:
                        archivo = pedir_nombre_archivo(stdscr)
                    guardar_archivo(lineas, archivo)
                    mostrar_mensaje = f"Archivo guardado en {archivo}"
                    mostrar_mensaje_color = curses.color_pair(6)
                    mostrar_mensaje_tiempo = time.time()
                    break
                elif comando_input == 'w':
                    if not archivo:
                        archivo = pedir_nombre_archivo(stdscr)
                    guardar_archivo(lineas, archivo)
                    mostrar_mensaje = f"Archivo guardado en {archivo}"
                    mostrar_mensaje_color = curses.color_pair(6)
                    mostrar_mensaje_tiempo = time.time()
                elif comando_input == 'l':
                    mostrar_lineas = not mostrar_lineas
                elif comando_input == 'copy':
                    if seleccionando and sel_inicio and sel_fin:
                        sy, sx = sel_inicio
                        ey, ex = sel_fin
                        if (sy, sx) > (ey, ex):
                            sy, sx, ey, ex = ey, ex, sy, sx
                        if sy == ey:
                            portapapeles = lineas[sy][sx:ex]
                        else:
                            temp = [lineas[sy][sx:]]
                            for y in range(sy+1, ey):
                                temp.append(lineas[y])
                            temp.append(lineas[ey][:ex])
                            portapapeles = '\n'.join(temp)
                        mostrar_mensaje = "Texto copiado"
                        mostrar_mensaje_color = curses.color_pair(6)
                        mostrar_mensaje_tiempo = time.time()
                elif comando_input == 'cortar':
                    if seleccionando and sel_inicio and sel_fin:
                        sy, sx = sel_inicio
                        ey, ex = sel_fin
                        if (sy, sx) > (ey, ex):
                            sy, sx, ey, ex = ey, ex, sy, sx
                        if sy == ey:
                            portapapeles = lineas[sy][sx:ex]
                            lineas[sy] = lineas[sy][:sx] + lineas[sy][ex:]
                        else:
                            temp = [lineas[sy][sx:]]
                            for y in range(sy+1, ey):
                                temp.append(lineas[y])
                            temp.append(lineas[ey][:ex])
                            portapapeles = '\n'.join(temp)
                            lineas[sy] = lineas[sy][:sx] + lineas[ey][ex:]
                            del lineas[sy+1:ey+1]
                        seleccionando = False
                        mostrar_mensaje = "Texto cortado"
                        mostrar_mensaje_color = curses.color_pair(6)
                        mostrar_mensaje_tiempo = time.time()
                elif comando_input == 'pegar':
                    if portapapeles:
                        parte = portapapeles.split('\n')
                        if len(parte) == 1:
                            lineas[cursor_y] = lineas[cursor_y][:cursor_x] + parte[0] + lineas[cursor_y][cursor_x:]
                            cursor_x += len(parte[0])
                        else:
                            linea_inicio = lineas[cursor_y][:cursor_x] + parte[0]
                            linea_fin = parte[-1] + lineas[cursor_y][cursor_x:]
                            lineas[cursor_y] = linea_inicio
                            for i in range(1, len(parte)-1):
                                lineas.insert(cursor_y+i, parte[i])
                            lineas.insert(cursor_y+len(parte)-1, linea_fin)
                            cursor_y += len(parte) - 1
                            cursor_x = len(parte[-1])
                        mostrar_mensaje = "Texto pegado"
                        mostrar_mensaje_color = curses.color_pair(6)
                        mostrar_mensaje_tiempo = time.time()
                elif comando_input.startswith('wf:'):
                    nuevo = comando_input[3:]
                    if nuevo:
                        guardar_archivo(lineas, nuevo)
                        mostrar_mensaje = f"Archivo guardado en {nuevo}"
                        mostrar_mensaje_color = curses.color_pair(6)
                        mostrar_mensaje_tiempo = time.time()
                comando = ''
                modo_comando = False
            elif key == 27:
                comando = ''
                modo_comando = False
            elif key in (8, 127, curses.KEY_BACKSPACE):
                comando = comando[:-1]
            else:
                if 0 < key < 256:
                    comando += chr(key)
        else:
            if key in (curses.KEY_BACKSPACE, 127):
                if cursor_x > 0:
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x - 1] + lineas[cursor_y][cursor_x:]
                    cursor_x -= 1
                elif cursor_y > 0:
                    prev_len = len(lineas[cursor_y - 1])
                    lineas[cursor_y - 1] += lineas[cursor_y]
                    del lineas[cursor_y]
                    cursor_y -= 1
                    cursor_x = prev_len
            elif key == curses.KEY_DC:
                if cursor_x < len(lineas[cursor_y]):
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x] + lineas[cursor_y][cursor_x+1:]
            elif key == curses.KEY_IC:
                modo_insertar = not modo_insertar
            elif key == curses.KEY_ENTER or key == 10:
                nueva = lineas[cursor_y][cursor_x:]
                lineas[cursor_y] = lineas[cursor_y][:cursor_x]
                lineas.insert(cursor_y + 1, nueva)
                cursor_y += 1
                cursor_x = 0
            elif key == curses.KEY_UP:
                if cursor_y > 0:
                    cursor_y -= 1
                    cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_DOWN:
                if cursor_y + 1 < len(lineas):
                    cursor_y += 1
                    cursor_x = min(cursor_x, len(lineas[cursor_y]))
            elif key == curses.KEY_LEFT:
                if cursor_x > 0:
                    cursor_x -= 1
            elif key == curses.KEY_RIGHT:
                if cursor_x < len(lineas[cursor_y]):
                    cursor_x += 1
            elif key == curses.KEY_HOME:
                cursor_x = 0
            elif key == curses.KEY_END:
                cursor_x = len(lineas[cursor_y])
            elif key == curses.KEY_PPAGE:
                cursor_y = max(cursor_y - (h - 3), 0)
            elif key == curses.KEY_NPAGE:
                cursor_y = min(cursor_y + (h - 3), len(lineas) - 1)
            elif 32 <= key <= 126:
                if modo_insertar or cursor_x >= len(lineas[cursor_y]):
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x] + chr(key) + lineas[cursor_y][cursor_x:]
                else:
                    lineas[cursor_y] = lineas[cursor_y][:cursor_x] + chr(key) + lineas[cursor_y][cursor_x + 1:]
                cursor_x += 1

            if seleccionando:
                sel_fin = (cursor_y, cursor_x)

            if cursor_y >= len(lineas):
                lineas.append("")

            if cursor_y < offset_y:
                offset_y = cursor_y
            elif cursor_y >= offset_y + h - 2:
                offset_y = cursor_y - (h - 3)

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
