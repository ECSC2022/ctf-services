package can

const CANFD_MAX_PAYLOAD = 64
const CAN_MTU = 16
const CANFD_MTU = 72
const CAN_EFF_FLAG uint32 = 0x80000000
const CAN_RTR_FLAG uint32 = 0x40000000
const CAN_ERR_FLAG uint32 = 0x20000000
const CAN_EXTENDED_MASK uint32 = 0x1FFFFFFF
const CAN_STANDARD_MASK uint32 = 0x000007FF