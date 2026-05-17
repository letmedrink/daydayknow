// 日志模块 - 支持日志级别控制

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  NONE = 4
}

// 从环境变量读取日志级别，默认 INFO
const LOG_LEVEL_MAP: Record<string, LogLevel> = {
  'debug': LogLevel.DEBUG,
  'info': LogLevel.INFO,
  'warn': LogLevel.WARN,
  'error': LogLevel.ERROR,
  'none': LogLevel.NONE
}

function getLogLevel(): LogLevel {
  const level = process.env.LOG_LEVEL?.toLowerCase() || 'info'
  return LOG_LEVEL_MAP[level] ?? LogLevel.INFO
}

// 格式化时间戳
function getTimestamp(): string {
  return new Date().toISOString()
}

// 格式化日志前缀
function formatPrefix(level: string, module?: string): string {
  const timestamp = getTimestamp()
  const moduleStr = module ? `[${module}]` : ''
  return `${timestamp} ${level} ${moduleStr}`
}

// 日志工具
export const logger = {
  debug(message: string, data?: any, module?: string) {
    if (getLogLevel() <= LogLevel.DEBUG) {
      const prefix = formatPrefix('DEBUG', module)
      if (data !== undefined) {
        console.log(`${prefix} ${message}`, typeof data === 'object' ? JSON.stringify(data, null, 2) : data)
      } else {
        console.log(`${prefix} ${message}`)
      }
    }
  },

  info(message: string, data?: any, module?: string) {
    if (getLogLevel() <= LogLevel.INFO) {
      const prefix = formatPrefix('INFO ', module)
      if (data !== undefined) {
        console.log(`${prefix} ${message}`, typeof data === 'object' ? JSON.stringify(data, null, 2) : data)
      } else {
        console.log(`${prefix} ${message}`)
      }
    }
  },

  warn(message: string, data?: any, module?: string) {
    if (getLogLevel() <= LogLevel.WARN) {
      const prefix = formatPrefix('WARN ', module)
      if (data !== undefined) {
        console.warn(`${prefix} ${message}`, typeof data === 'object' ? JSON.stringify(data, null, 2) : data)
      } else {
        console.warn(`${prefix} ${message}`)
      }
    }
  },

  error(message: string, error?: any, module?: string) {
    if (getLogLevel() <= LogLevel.ERROR) {
      const prefix = formatPrefix('ERROR', module)
      if (error instanceof Error) {
        console.error(`${prefix} ${message}`, {
          message: error.message,
          stack: error.stack
        })
      } else if (error !== undefined) {
        console.error(`${prefix} ${message}`, typeof error === 'object' ? JSON.stringify(error, null, 2) : error)
      } else {
        console.error(`${prefix} ${message}`)
      }
    }
  },

  // 创建模块化日志器
  module(name: string) {
    return {
      debug: (message: string, data?: any) => logger.debug(message, data, name),
      info: (message: string, data?: any) => logger.info(message, data, name),
      warn: (message: string, data?: any) => logger.warn(message, data, name),
      error: (message: string, error?: any) => logger.error(message, error, name),
    }
  }
}

export default logger