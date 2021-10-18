/*
** rigol keygen / cybernet & the-eevblog-users
**
** to compile this you need MIRACL from [url]https://github.com/CertiVox/MIRACL[/url]
** download the master.zip into a new folder and run 'unzip -j -aa -L master.zip'
** then run 'bash linux' to build the miracle.a library
**
** BUILD WITH:
**
** more info: http://www.eevblog.com/forum/testgear/sniffing-the-rigol's-internal-i2c-bus/
*/

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <ctype.h>
#include "miracl.h"
#include "config.h"
#include "options.h"

char version[]             = "Riglol " riglol_VERSION_MAJOR "." riglol_VERSION_MINOR "."riglol_VERSION_PATCH " " SYSTEM;
char DP832_private_key[]   = "5C393C30FACCF4";
char DS2000_private_key[]  = "8EEBD4D04C3771";
char DSA815_private_key[]  = "80444DFECE903E";
char DS1000Z_private_key[] = "6F1106DDA994DA";
char MSO1000Z_private_key[] = "99FC5DFBE778D0";
char DG1000Z_private_key[] = "7412E98108CAB0";	//publ: 0x586E719859AF6C

static char* ascii_map;
static const char ascii_map_dg[] = "MNBVCXZASDFGHJKLPUYTREWQ23456789";
static const char ascii_map_[]   = "23456789ASDFGHJKLPUYTREWQMNBVCXZ";

char no_private_key[]      = "";

/*
** sign the secret message (serial + opts) with the private key
*/
void ecssign(char *serial, char *options, char *privk, char *lic1, char *lic2) {
    char prime1[]  = "AEBF94CEE3E707";
    char prime2[]  = "AEBF94D5C6AA71";
    char curve_a[] = "2982";
    char curve_b[] = "3408";
    char point1[]  = "7A3E808599A525";
    char point2[]  = "28BE7FAFD2A052";
    int k_offset = 0; // optionally change ecssign starting offset (changes lic1; makes different licenses)
    mirsys(800, 16)->IOBASE = 16;

    sha sha1;
    shs_init(&sha1);

    char *ptr = serial;
    while(*ptr) shs_process(&sha1, *ptr++);
    ptr = options;
    while(*ptr) shs_process(&sha1, *ptr++);

    char h[20];
    shs_hash(&sha1, h);
    big hash = mirvar(0);
    bytes_to_big(20, h, hash);

    big a = mirvar(0);
    instr(a, curve_a);
    big b = mirvar(0);
    instr(b, curve_b);
    big p = mirvar(0);
    instr(p, prime1);
    big q = mirvar(0);
    instr(q, prime2);
    big Gx = mirvar(0);
    instr(Gx, point1);
    big Gy = mirvar(0);
    instr(Gy, point2);
    big d = mirvar(0);
    instr(d, privk);
    big k = mirvar(0);
    big r = mirvar(0);
    big s = mirvar(0);
    big k1 = mirvar(0);
    big zero = mirvar(0);

    big f1 = mirvar(17);
    big f2 = mirvar(53);
    big f3 = mirvar(905461);
    big f4 = mirvar(60291817);

    incr(k, k_offset, k);

    epoint *G = epoint_init();
    epoint *kG = epoint_init();
    ecurve_init(a, b, p, MR_PROJECTIVE);
    epoint_set(Gx, Gy, 0, G);

    for(;;) {
        incr(k, 1, k);

        if(divisible(k, f1) || divisible(k, f2) || divisible(k, f3) || divisible(k, f4))
            continue;

        ecurve_mult(k, G, kG);
        epoint_get(kG, r, r);
        divide(r, q, q);

        if(mr_compare(r, zero) == 0)
            continue;

        xgcd(k, q, k1, k1, k1);
        mad(d, r, hash, q, q, s);
        mad(s, k1, k1, q, q, s);

        if(!divisible(s, f1) && !divisible(s, f2) && !divisible(s, f3) && !divisible(s, f4))
            break;
    }

    cotstr(r, lic1);
    cotstr(s, lic2);
}

/*
** convert string to uppercase chars
*/
char *strtoupper(char *str) {
    char *p;
    for (p=str; *p; p++)
        *p = toupper(*p);
    return str;
}

/*
** prepend a char to a string
*/
char *prepend(char *c, char *str) {
    int i;

    for (i = strlen(str); i >= 0; i--) {
        str[i + 1] = str[i];
    }

    str[0] = *c;
    return c;
}

/*
** convert hex-ascii-string to rigol license format
*/
void map_hex_to_rigol(char *io) {
    unsigned long long b = 0;
    int i = 0;
    char map[] = {
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
        'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R',
        'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
        '2', '3', '4', '5', '6', '7', '8', '9'
    };

    /* hex2dez */
    while (io[i] != '\0') {
        if (io[i] >= '0' && io[i] <= '9') {
            b = b * 16 + io[i] - '0';
        } else if (io[i] >= 'A' && io[i] <= 'F') {
            b = b * 16 + io[i] - 'A' + 10;
        } else if (io[i] >= 'a' && io[i] <= 'f') {
            b = b * 16 + io[i] - 'a' + 10;
        }
        i++;
    }

    for (i = 3; ; i--) {
        io[i] = map[b & 0x1F];
        if (i == 0) break;
        b >>= 5;
    }

    io[4] = '\0';
}

char *get_version() {
  char *v;

  v=version;
  return v;
}

void show_device_options() {
	for (size_t i = 0; i < sizeof(riglol_devices)/sizeof(riglol_devices[0]); i++) {
		struct riglol_device *dev = riglol_devices[i];
		printf("%s %s options:\n", dev->name, dev->description);
		if (strlen(dev->notes))
			printf("  %s\n", dev->notes);
		for (size_t opt = 0; opt < dev->num_options; opt++)
			printf("  %s - %s\n", dev->options[opt].code, dev->options[opt].description);
		printf("\n");
	}
}

void show_help(char *cmd) {
    printf("%s\n", get_version());
    printf("\n");
    printf("Usage: %s <sn> <opts> <privkey>\n", cmd);
    printf("  <sn>       serial number of device (D............)\n");
    printf("  <opts>     device options, 4 characters, see below\n");
    printf("  <privkey>  private key (optional)\n");
    printf("\n");
	 show_device_options();
    printf("MAKE SURE YOUR FIRMWARE IS UP TO DATE BEFORE APPLYING ANY KEYS\n");
}

//static const char ascii_map[] = "23456789ASDFGHJKLPUYTREWQMNBVCXZ";

static int ascii_to_bin(char c)
{
    int i;

    for (i = 0; i < sizeof(ascii_map_)-1; i++)
        if (ascii_map[i] == c)
            break;
    return i;
}

static char *options_4to5(const char *opt4, char *opt5)
{
    int map[] = { 0, 3, 2, 1 };
    int i, opt = 0;

    for (i = 0; i < 4; i++)
        opt = (opt << 5) | ascii_to_bin(opt4[map[i]]);
    for (i = 0; i < 5; i++) {
        opt5[i] = ascii_map[opt & 0x0F];
        opt >>= 4;
    }
    opt5[i] = 0;
    return opt5;
}

static void format_license_dp832_109(char *lic1_code, char *lic2_code,
                                     char *options, char *licence, int isDG)
{
    const int map1dp[] = { 4, 11, 16, 23, 0, 24, 6, 22, 8, 20, 18, 25 };
    const int map2dp[] = { 3, 14, 19, 9, 26, 5, 1, 10, 12, 13, 15, 21 };
    const int map3dp[] = { 2, 7, 17, 27 };

    const int map1dg[] = {3, 0xE, 0x13, 9, 0x1A, 5, 7, 0x11, 0xC, 0x18, 6, 0x16};
    const int map2dg[] = {4, 0xB, 0x10, 0x17, 0, 8, 0x14, 0x1B, 2, 0xD, 0xF, 0x15};
    const int map3dg[] = {1, 0xA, 0x12, 0x19};

    const int *map1 = isDG?map1dg:map1dp;
    const int *map2 = isDG?map2dg:map2dp;
    const int *map3 = isDG?map3dg:map3dp;
    unsigned long long k;
    int i;

    k = strtoll(lic1_code, NULL, 16);
    for (i = 0; k < (1ULL << 51); i++)
        k = (k << 4) | 0;
    k = (k << 4) | i;
    for (i = 0; i < 12; i++) {
        licence[map1[i]] = ascii_map[k & 0x1F];
        k >>= 5;
    }

    k = strtoll(lic2_code, NULL, 16);
    for (i = 0; k < (1ULL << 51); i++)
        k = (k << 4) | 5;
    k = (k << 4) | i;
    for (i = 0; i < 12; i++) {
        licence[map2[i]] = ascii_map[k & 0x1F];
        k >>= 5;
    }

    if (isDG) {
        int map[] = { 0, 3, 2, 1 };
	char *opt = strdup(options);
	for (i = 0; i < 4; i++)
	    opt[i] = options[map[i]];
	for (i = 0; i < 4; i++)
	    licence[map3[i]] = opt[3 - i];
        free(opt);
    }
    else
	for (i = 0; i < 4; i++)
	    licence[map3[i]] = options[i];

    licence[28] = 0;
}

static void format_license_classic(char *lic1_code, char *lic2_code,
                                   char *options, char *licence)
{
    char *lic_all, *chunk, *temp;
    int i, j;

    /* fix missing zeroes */
    while (strlen(lic1_code) < 14) {
        prepend("0", lic1_code);
    }
    while (strlen(lic2_code) < 14) {
        prepend("0", lic2_code);
    }

    /* combine lic1 and lic2 */
    lic_all = (char*)calloc(128, 1);
    temp = (char*)calloc(128, 1);
    chunk = (char*)calloc(6, 1);
    strcpy(lic_all, lic1_code);
    strcat(lic_all, "0");
    strcat(lic_all, lic2_code);
    strcat(lic_all, "0");

    /* generate serial */
    i=0;
    while (i < strlen(lic_all)) {
        memcpy(chunk, lic_all + i, 5);
        map_hex_to_rigol(chunk);
        strcat(temp, chunk);
        i = i + 5;
    }

    /* add options and "-" */
    j = 0;
    for(i = 0; i <= strlen(temp); ) {
       switch(j) {
         case 1:  licence[j] = options[0];  break;
         case 7:  licence[j] = '-';         break;
         case 10: licence[j] = options[1];  break;
         case 15: licence[j] = '-';         break;
         case 19: licence[j] = options[2];  break;
         case 23: licence[j] = '-';         break;
         case 28: licence[j] = options[3];  break;
         default: licence[j] = temp[i];
                  i++;
       }
       j++;
    }
    licence[j] = '\0';

    /* cleen up */
    free(lic_all);
    free(chunk);
    free(temp);
}

char *make_licence(char *serial, char *options, char* priv_key)
{
    char options_buffer[8], *opts = options;
    char *lic1_code, *lic2_code, *lic_all;
    char *chunk, *temp, *licence;
    int i, j;

    /* convert string to uppercase chars */
    strtoupper(serial);
    strtoupper(options);
    strtoupper(priv_key);

    int isDG = strncmp(serial, "DG1", 3)?0:1;
    /* convert options string format for DP832 with firmware >= 1.09 or for DG1000Z*/
    if ((!strncmp(serial, "DP8", 3) && options[0] != 'M' && options[0] != '5') || isDG)
        opts = options_4to5(options, options_buffer);

    /* sign the message */
    lic1_code = (char*)calloc(64, 1);
    lic2_code = (char*)calloc(64, 1);
    ecssign(serial, opts, priv_key, lic1_code, lic2_code);

    /* format licence string */
    licence = (char*)calloc(128, 1);
	if ((!strncmp(serial, "DP8", 3) && *options != 'M' && *options != '5') || isDG)
        format_license_dp832_109(lic1_code, lic2_code, options, licence, isDG);
    else
        format_license_classic(lic1_code, lic2_code, options, licence);

    /* cleen up */
    free(lic1_code);
    free(lic2_code);

    return licence;
}

char *select_priv_key(char *serial) {
    char *priv_key;

    strtoupper(serial);
    if      (!strncmp(serial, "DS1ZD", 5)) priv_key = MSO1000Z_private_key;
    else if (!strncmp(serial, "DS1", 3)) priv_key = DS1000Z_private_key;
    else if (!strncmp(serial, "DS2", 3)) priv_key = DS2000_private_key;
    else if (!strncmp(serial, "DS4", 3)) priv_key = DS2000_private_key;
    else if (!strncmp(serial, "DSA", 3)) priv_key = DSA815_private_key;
    else if (!strncmp(serial, "DP8", 3)) priv_key = DP832_private_key;
    else if (!strncmp(serial, "DG1", 3)) priv_key = DG1000Z_private_key;
    else                                 priv_key = no_private_key;

    return priv_key;
}

int main(int argc, char *argv[0]) {
    char *serial, *options, *priv_key, *licence;

    /* parse input */
    if (!((argc == 3 || argc == 4))) {
        show_help(argv[0]);
        exit(1);
    }
    serial = argv[1];
    options = argv[2];

    ascii_map = strncmp(serial, "DG1", 3)?(char*)ascii_map_:(char*)ascii_map_dg;

    if (argc == 4) priv_key = argv[3];
    else {
        priv_key = select_priv_key(serial);
        if (strlen(priv_key) == 0) {
            show_help(argv[0]);
            printf("\nERROR: UNKNOW DEVICE WITHOUT PRIVATKEY\n");
            exit(1);
        }
    }

    if (strlen(priv_key) != 14) {
        show_help(argv[0]);
        printf("\nERROR: INVALID PRIVATE KEY LENGTH\n");
        exit(1);
    }
    if (strlen(serial) < 13) {
        show_help(argv[0]);
        printf("\nERROR: INVALID SERIAL LENGTH\n");
        exit(1);
    }
    if (strlen(options) != 4) {
        show_help(argv[0]);
        printf("\nERROR: INVALID OPTIONS LENGTH\n");
        exit(1);
    }

    licence = make_licence(serial, options, priv_key);
    printf("%s\n", licence);
    free(licence);
}
