import sys
import struct
from tableprint import columnprint

# http://opensource.apple.com/source/xnu/xnu-xxxx.xx.xx/bsd/sys/sysent.h



sy_return_type = {
    0: 'NONE',
    1: 'INT',
    2: 'UINT',
    3: 'OFFSET',
    4: 'ADDRESS',
    5: 'SIZE',
    6: 'SSIZE', # Length : [-1, {SSIZE_MAX}]
    7: 'UINT64'
}

# SN/Lion 32bit, SN/Lion/ML 64bit, Mavericks
DATA_SYSCALL_TABLE_STRUCTURE = [[24, '=h2xIIIII'], [40, '=I4xQQQII'], [32, '=QQQIHH'], [24, '=QQIHH']]


class systab_manager():
    def __init__(self, x86_mem_pae, arch, os_version, build, base_address):
        self.x86_mem_pae = x86_mem_pae
        self.arch = arch
        self.os_version = os_version
        self.build = build
        self.base_address = base_address

    def get_syscall_table(self, sym_addr): # 11.11.23 64bit suppport
        syscall_list = []
        if self.os_version <= 12:
            if self.arch == 32:
                SYSCALL_TABLE_STRUCTURE = DATA_SYSCALL_TABLE_STRUCTURE[0]
                nsysent = self.x86_mem_pae.read(sym_addr + self.base_address, 4) # .data _nsysent
                data = struct.unpack('I', nsysent) # uint32
            elif self.arch == 64:
                SYSCALL_TABLE_STRUCTURE = DATA_SYSCALL_TABLE_STRUCTURE[1]
                nsysent = self.x86_mem_pae.read(sym_addr + self.base_address, 8) # .data _nsysent
                data = struct.unpack('Q', nsysent)
        elif self.os_version == 13: # Mavericks
            SYSCALL_TABLE_STRUCTURE = DATA_SYSCALL_TABLE_STRUCTURE[2]
            nsysent = self.x86_mem_pae.read(sym_addr + self.base_address, 8) # .data _nsysent
            data = struct.unpack('Q', nsysent)
        elif self.os_version == 14: # Yosemite
            SYSCALL_TABLE_STRUCTURE = DATA_SYSCALL_TABLE_STRUCTURE[3]
            nsysent = self.x86_mem_pae.read(sym_addr + self.base_address, 8) # .data _nsysent
            data = struct.unpack('Q', nsysent)

        else:
            print '[+] systab support Snow Leopard ~ Yosemite'
            return syscall_list

        if self.os_version <= 12:
            if self.os_version == '12': # mountain lion
                sysentaddr = sym_addr + self.base_address + 0x1C028 # mountain lion
            else:
                sysentaddr = sym_addr - (data[0] * SYSCALL_TABLE_STRUCTURE[0])# sysent structure size + 2bytes

            for count in range(0, data[0]):
                sysent = self.x86_mem_pae.read(sysentaddr + (count*SYSCALL_TABLE_STRUCTURE[0]), SYSCALL_TABLE_STRUCTURE[0]); # .data _nsysent
                data = struct.unpack(SYSCALL_TABLE_STRUCTURE[1], sysent) # uint32

                syscall_list.append(data)
        elif self.os_version == 13: # Mavericks
            sysentaddr = sym_addr + self.base_address + 0x19818# Mavericks
            #print '%x'%self.x86_mem_pae.vtop(sysentaddr)
            for count in range(0, data[0]):
                tmplist = []
                sysent = self.x86_mem_pae.read(sysentaddr + (count*SYSCALL_TABLE_STRUCTURE[0]), SYSCALL_TABLE_STRUCTURE[0]); # .data _nsysent
                data = struct.unpack(SYSCALL_TABLE_STRUCTURE[1], sysent) # uint32
                tmplist.append(data[4]) # number of args
                tmplist.append(data[0]) # system call
                tmplist.append(data[1]) # system call arguments munger for 32-bit process
                tmplist.append(data[2]) # system call arguments munger for 64-bit process
                tmplist.append(data[3]) # system call return types
                tmplist.append(data[5]) #  Total size of arguments bytes for 32bit system calls

        elif self.os_version == 14: # Yosemite
            if self.build == '14D136' or '14E46' or '14F27':
                sysentaddr = sym_addr + self.base_address - 0x6BDA8
            else:    
                sysentaddr = sym_addr + self.base_address - 0x69978
            #print '%x'%self.x86_mem_pae.vtop(sysentaddr)
            for count in range(0, data[0]):
                tmplist = []
                sysent = self.x86_mem_pae.read(sysentaddr + (count*SYSCALL_TABLE_STRUCTURE[0]), SYSCALL_TABLE_STRUCTURE[0]); # .data _nsysent
                data = struct.unpack(SYSCALL_TABLE_STRUCTURE[1], sysent) # uint32
                tmplist.append(data[3]) # number of args
                tmplist.append(data[0]) # system call
                tmplist.append(0X00) # Not Available on Yosemite
                tmplist.append(data[1]) # system call arguments munger for 64-bit process
                tmplist.append(data[2]) # system call return types
                tmplist.append(data[4]) #  Total size of arguments bytes for 32bit system calls

                syscall_list.append(tmplist)
            #print '%x'%self.x86_mem_pae.vtop(sysentaddr + (count*SYSCALL_TABLE_STRUCTURE[0]))


    
        return syscall_list

#################################### PUBLIC FUNCTIONS ####################################

def print_syscall_table(data_list, symbol_list, base_address):
    #data_list = m_volafox.systab(symbol_list['_nsysent'])
    sym_name_list = symbol_list.keys()
    sym_addr_list = symbol_list.values()
    print '[+] Syscall List'
    headerlist = ["NUM","ARG_COUNT", "NAME", "CALL_PTR", "ARG_MUNGE32_PTR", "ARG_MUNGE64_PTR", "RET_TYPE", "ARG_BYTES", "HOOK_FINDER"]
    contentlist = []
    
    count = 0
    for data in data_list:
        symflag = 0
        line = ['%d'%count]
        line.append('%d'%data[0])
        i = 0
        for sym_addr in sym_addr_list:
            if data[1] == sym_addr+base_address:
                line.append('%s'%sym_name_list[i])
                symflag = 1
            i += 1
        if symflag != 1:
            line.append('0x%.8X'%data[1])
        line.append('0x%.8X'%data[1])
        line.append('0x%.8X'%data[2])
        line.append('0x%.8X'%data[3])
        try:
            line.append('%s'%sy_return_type[data[4]])
        except:
            line.append('%d'%data[4])
        line.append('%d'%data[5])
        if symflag == 1:
            line.append('True')
        else:
            line.append('Maybe hooked')
        count += 1
        contentlist.append(line)

    mszlist = [-1, -1, -1, -1, -1, -1, -1, -1, -1]
    columnprint(headerlist, contentlist, mszlist) 

def get_system_call_table_list(x86_mem_pae, sym_addr, arch, os_version, build, base_address):
    SYSCALLMan = systab_manager(x86_mem_pae, arch, os_version, build, base_address)
    syscall_list = SYSCALLMan.get_syscall_table(sym_addr)
    return syscall_list
