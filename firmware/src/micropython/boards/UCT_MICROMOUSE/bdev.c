#include "py/obj.h"
#include "storage.h"
#include "ZD25WQ80C.h"
#include <string.h>

#define PARTITION_START_ADDR  0xE0000 // Last 128KB of 1MB chip
#define NUM_BLOCKS            256     // 128KB / 512 bytes = 256 logical blocks
#define BLOCK_SIZE            512     // FAT block size
#define SEC_SIZE              4096    // Physical sector size of ZD25WQ80C

// Expose the global flash driver handle from the template
extern ZD25WQ80C_t flash;

// Temporary sector cache buffer to handle 512-byte sub-sector writes
static uint8_t sector_cache[SEC_SIZE];
static uint32_t cached_sector_addr = 0xFFFFFFFFU;
static bool cache_dirty = false;

// Initialize flash if not done yet
static int ext_flash_init(void) {
    if (!flash.initialized) {
        if (!initZD25WQ80C()) {
            return -1;
        }
    }
    return 0;
}

// Flush the cache
static int ext_flash_flush(void) {
    if (cache_dirty && cached_sector_addr != 0xFFFFFFFFU) {
        // Erase the physical sector
        if (ZD25WQ80C_SectorErase(cached_sector_addr) != HAL_OK) {
            return -1;
        }
        // Write the cached sector back using PageProgram in 256-byte chunks
        for (uint32_t offset = 0; offset < SEC_SIZE; offset += ZD25WQ80C_PAGE_SIZE) {
            if (ZD25WQ80C_PageProgram(cached_sector_addr + offset, sector_cache + offset, ZD25WQ80C_PAGE_SIZE) != HAL_OK) {
                return -1;
            }
        }
        cache_dirty = false;
    }
    return 0;
}

// Read blocks
int uct_bdev_readblocks(uint8_t *dest, uint32_t block_num, uint32_t num_blocks) {
    if (ext_flash_init() < 0) return -1;

    for (uint32_t i = 0; i < num_blocks; i++) {
        uint32_t logical_block = block_num + i;
        uint32_t byte_addr = PARTITION_START_ADDR + logical_block * BLOCK_SIZE;
        uint32_t sector_addr = byte_addr & ~(SEC_SIZE - 1);
        uint32_t sector_offset = byte_addr & (SEC_SIZE - 1);

        if (sector_addr == cached_sector_addr) {
            // Read from cache
            memcpy(dest + i * BLOCK_SIZE, sector_cache + sector_offset, BLOCK_SIZE);
        } else {
            // If the sector is not cached, read directly from flash
            if (ZD25WQ80C_Read(byte_addr, dest + i * BLOCK_SIZE, BLOCK_SIZE) != HAL_OK) {
                return -1;
            }
        }
    }
    return 0;
}

// Write blocks
int uct_bdev_writeblocks(const uint8_t *src, uint32_t block_num, uint32_t num_blocks) {
    if (ext_flash_init() < 0) return -1;

    for (uint32_t i = 0; i < num_blocks; i++) {
        uint32_t logical_block = block_num + i;
        uint32_t byte_addr = PARTITION_START_ADDR + logical_block * BLOCK_SIZE;
        uint32_t sector_addr = byte_addr & ~(SEC_SIZE - 1);
        uint32_t sector_offset = byte_addr & (SEC_SIZE - 1);

        if (sector_addr != cached_sector_addr) {
            // Flush old cache if dirty
            if (ext_flash_flush() < 0) return -1;

            // Load new sector into cache
            if (ZD25WQ80C_Read(sector_addr, sector_cache, SEC_SIZE) != HAL_OK) {
                return -1;
            }
            cached_sector_addr = sector_addr;
        }

        // Copy source block to cache
        memcpy(sector_cache + sector_offset, src + i * BLOCK_SIZE, BLOCK_SIZE);
        cache_dirty = true;
    }
    return 0;
}

// IOCTL handler
int uct_bdev_ioctl(uint32_t op, uint32_t arg) {
    switch (op) {
        case BDEV_IOCTL_INIT:
            return ext_flash_init();
        case BDEV_IOCTL_SYNC:
            return ext_flash_flush();
        case BDEV_IOCTL_NUM_BLOCKS:
            return NUM_BLOCKS;
        case BDEV_IOCTL_IRQ_HANDLER:
            return 0;
    }
    return -1;
}
