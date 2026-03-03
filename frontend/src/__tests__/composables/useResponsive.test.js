import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useResponsive } from '../../composables/useResponsive.js'

describe('useResponsive', () => {
  let originalInnerWidth
  
  beforeEach(() => {
    originalInnerWidth = window.innerWidth
  })
  
  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      value: originalInnerWidth,
      writable: true
    })
  })

  it('should detect mobile screen', () => {
    Object.defineProperty(window, 'innerWidth', {
      value: 400,
      writable: true
    })
    
    const { isMobile } = useResponsive()
    expect(isMobile.value).toBe(true)
  })

  it('should detect tablet screen', () => {
    Object.defineProperty(window, 'innerWidth', {
      value: 800,
      writable: true
    })
    
    const { isTablet } = useResponsive()
    expect(isTablet.value).toBe(true)
  })

  it('should detect desktop screen', () => {
    Object.defineProperty(window, 'innerWidth', {
      value: 1200,
      writable: true
    })
    
    const { isDesktop } = useResponsive()
    expect(isDesktop.value).toBe(true)
  })

  it('should return correct grid columns', () => {
    // Mobile
    Object.defineProperty(window, 'innerWidth', { value: 400, writable: true })
    let { gridCols } = useResponsive()
    expect(gridCols.value).toBe(1)
    
    // Tablet
    Object.defineProperty(window, 'innerWidth', { value: 800, writable: true })
    ;({ gridCols } = useResponsive())
    expect(gridCols.value).toBe(2)
    
    // Desktop
    Object.defineProperty(window, 'innerWidth', { value: 1024, writable: true })
    ;({ gridCols } = useResponsive())
    expect(gridCols.value).toBe(3)
    
    // Large screen
    Object.defineProperty(window, 'innerWidth', { value: 1400, writable: true })
    ;({ gridCols } = useResponsive())
    expect(gridCols.value).toBe(4)
  })
})
