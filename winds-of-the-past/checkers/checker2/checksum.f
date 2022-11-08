! gfortran exploit2_checksum.f -fdec-structure -o exploit2_checksum

      PROGRAM CHECKSUM
        STRUCTURE /TURBINE/
            CHARACTER(len=36) id
            CHARACTER(len=128) checksum
            CHARACTER(len=512) description
            INTEGER modelnumber
        END STRUCTURE

        RECORD /TURBINE/ turbine
        INTEGER :: modelnumber
        CHARACTER(len=64) :: turbine_id, turbine_modelnumber

        CALL getarg(1, turbine_id)
        CALL getarg(2, turbine_modelnumber)

        turbine%id = turbine_id
        READ(turbine_modelnumber,"(I1)") turbine%modelnumber

        WRITE(*,"(A)") calculate_checksum(turbine)
      CONTAINS

        ! Copied from mod_crypto.f / mod_turbine.f
        FUNCTION get_diffusion_val(idx)
            INTEGER :: get_diffusion_val
            INTEGER :: SBOX(256) = (/99, 124, 119, 123, 242, 107
     c           ,111, 197, 48, 1, 103, 43, 254, 215, 253, 118,
     c           202, 130, 201, 125, 250, 89, 71, 240, 173, 212,
     c           162, 175, 156, 164, 114, 192, 183, 253, 147, 38,
     c           54, 63, 247, 204, 52, 165, 229, 241, 113, 216,
     c           49, 21, 4, 199, 35, 195, 24, 150, 5, 154,
     c           7, 18, 128, 226, 235, 39, 178, 117, 9, 131,
     c           44, 26, 27, 110, 90, 160, 82, 59, 214, 179,
     c           41, 227, 47, 132, 83, 209, 0, 237, 32, 252,
     c           177, 91, 106, 203, 190, 57, 74, 76, 88, 207,
     c           208, 239, 170, 251, 67, 77, 51, 133, 69, 249,
     c           2, 127, 80, 60, 159, 168, 81, 163, 64, 143,
     c           146, 157, 56, 245, 188, 182, 218, 33, 16, 255,
     c           243, 210, 205, 12, 19, 236, 95, 151, 68, 23,
     c           196, 167, 126, 61, 100, 93, 25, 115, 96, 129,
     c            79, 220, 34, 42, 144, 136, 70, 238, 184, 20,
     c           222, 94, 11, 219, 224, 50, 58, 10, 73, 6,
     c           36, 92, 194, 211, 172, 98, 145, 149, 228, 121,
     c          231, 200, 55, 109, 141, 213, 78, 169, 108, 86,
     c          244, 234, 101, 122, 174, 8, 186, 120, 37, 46,
     c          28, 166, 180, 198, 232, 221, 116, 31, 75, 189,
     c          139, 138, 112, 62, 181, 102, 72, 3, 246, 14,
     c          97, 53, 87, 185, 134, 193, 29, 158, 225, 248,
     c          152, 17, 105, 217, 142, 148, 155, 30, 135, 233,
     c          206, 85, 40, 223, 140, 161, 137, 13, 191, 230,
     c          66, 104, 65, 153, 45, 15, 176, 84, 187, 22/)
            INTEGER,INTENT(IN) :: idx

              get_diffusion_val = SBOX(idx)
              RETURN
        END FUNCTION get_diffusion_val

        FUNCTION calculate_checksum(turbine)
            RECORD /TURBINE/,INTENT(IN) :: turbine
            CHARACTER(len=128) :: calculate_checksum, checksum
            CHARACTER(len=2) :: byte_buffer
            INTEGER :: i, j, a, b, c, value

            checksum = REPEAT("0", LEN(checksum))

            j = 1
            DO i = 1, LEN(turbine%id) / 2
                a = ICHAR(turbine%id(i:i))
                b = ICHAR(turbine%id(36 - i:36 - i))
                c = INT(get_diffusion_val(MOD(a + b, 256) + 1))
                value = iEOR(b,IEOR(i, IEOR(a,
     c          IEOR(b, turbine%modelnumber))))
                WRITE(byte_buffer,"(Z0.2)") value
                checksum(j:j + 1) = byte_buffer
                j = j + 2
            END DO

            calculate_checksum = checksum
        END FUNCTION calculate_checksum
      END PROGRAM CHECKSUM
