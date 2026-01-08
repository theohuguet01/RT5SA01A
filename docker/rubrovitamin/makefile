# makefile pour carte a puce
# $ make
# $ make clean
# $ make progcarte
# $ make progcarte_eeprom
# $ make fuses

NAME     = rubro_v2
PROGNAME = $(NAME).hex
EENAME   = $(NAME).eep

PROC = -mmcu=atmega328p
AVR  = avr5

CC   = avr-gcc
IDIR = -I/usr/lib/avr/include/avr
LDIR = -L/usr/lib/avr/lib/$(AVR)/

AVRDUDE    = avrdude
PROGRAMMER = arduino
PART       = atmega328p
BAUD       = 115200

all: $(NAME).elf
        avr-objcopy -R .eeprom -R .eesafe -R .fuse -R .lock -R .signature -O ihex $(NAME).elf $(PROGNAME)
        avr-objcopy --no-change-warnings -j .eeprom --change-section-lma .eeprom=0 -O ihex $(NAME).elf $(EENAME)

$(NAME).elf: $(NAME).o io.o
        avr-gcc -o $(NAME).elf $(NAME).o io.o $(LDIR) $(PROC)

clean:
        rm -f $(NAME).elf *.o $(NAME).eep $(NAME).hex

$(NAME).o: $(NAME).c
        $(CC) -c -Wall -Ofast $(NAME).c $(PROC) $(IDIR)

io.o: io.c
        $(CC) -c -Wall io.c $(PROC) $(IDIR)

# FLASH uniquement (fiable dans ton mode bootloader)
progcarte:
        echo "Programmation de la carte (FLASH uniquement)"
        @if [ -e /dev/ttyACM0 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyACM0 -b $(BAUD) -U flash:w:"./$(PROGNAME)":i; fi
        @if [ -e /dev/ttyACM1 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyACM1 -b $(BAUD) -U flash:w:"./$(PROGNAME)":i; fi
        @if [ -e /dev/ttyUSB0 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyUSB0 -b $(BAUD) -U flash:w:"./$(PROGNAME)":i; fi
        @if [ -e /dev/ttyUSB1 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyUSB1 -b $(BAUD) -U flash:w:"./$(PROGNAME)":i; fi

# FLASH + EEPROM (best effort : chez toi la vérif EEPROM échoue)
progcarte_eeprom:
        echo "Programmation de la carte (FLASH + EEPROM - best effort)"
        @if [ -e /dev/ttyACM0 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyACM0 -b $(BAUD) \
                        -U flash:w:"./$(PROGNAME)":i -U eeprom:w:"./$(EENAME)":i; fi
        @if [ -e /dev/ttyACM1 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyACM1 -b $(BAUD) \
                        -U flash:w:"./$(PROGNAME)":i -U eeprom:w:"./$(EENAME)":i; fi
        @if [ -e /dev/ttyUSB0 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyUSB0 -b $(BAUD) \
                        -U flash:w:"./$(PROGNAME)":i -U eeprom:w:"./$(EENAME)":i; fi
        @if [ -e /dev/ttyUSB1 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -P /dev/ttyUSB1 -b $(BAUD) \
                        -U flash:w:"./$(PROGNAME)":i -U eeprom:w:"./$(EENAME)":i; fi

# Fuses (souvent non supporté via bootloader)
fuses:
        echo "Programmation des fusibles (peut échouer via bootloader)"
        @if [ -e /dev/ttyACM0 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -b $(BAUD) -P /dev/ttyACM0 \
                        -U efuse:w:0xff:m -U efuse:w:0xff:m -U hfuse:w:0xd9:m; fi
        @if [ -e /dev/ttyACM1 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -b $(BAUD) -P /dev/ttyACM1 \
                        -U efuse:w:0xff:m -U efuse:w:0xff:m -U hfuse:w:0xd9:m; fi
        @if [ -e /dev/ttyUSB0 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -b $(BAUD) -P /dev/ttyUSB0 \
                        -U efuse:w:0xff:m -U efuse:w:0xff:m -U hfuse:w:0xd9:m; fi
        @if [ -e /dev/ttyUSB1 ]; then\
                $(AVRDUDE) -c $(PROGRAMMER) -p $(PART) -b $(BAUD) -P /dev/ttyUSB1 \
                        -U efuse:w:0xff:m -U efuse:w:0xff:m -U hfuse:w:0xd9:m; fi
