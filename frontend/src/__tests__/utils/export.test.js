import { describe, it, expect, vi } from 'vitest'
import { exportCSV, exportJSON } from '../../utils/export.js'

describe('Export Utils', () => {
  // Mock URL.createObjectURL and URL.revokeObjectURL
  global.URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  global.URL.revokeObjectURL = vi.fn()
  
  // Mock document methods
  const mockClick = vi.fn()
  const mockAppendChild = vi.fn()
  const mockRemoveChild = vi.fn()
  
  Object.defineProperty(document, 'createElement', {
    value: vi.fn(() => ({
      click: mockClick,
      href: '',
      download: ''
    }))
  })
  
  Object.defineProperty(document.body, 'appendChild', {
    value: mockAppendChild
  })
  
  Object.defineProperty(document.body, 'removeChild', {
    value: mockRemoveChild
  })

  describe('exportCSV', () => {
    it('should export CSV with correct format', () => {
      const data = [
        { name: 'Test 1', value: 100 },
        { name: 'Test 2', value: 200 }
      ]
      const headers = [
        { key: 'name', label: 'Name' },
        { key: 'value', label: 'Value' }
      ]
      
      exportCSV(data, headers, 'test.csv')
      
      expect(document.createElement).toHaveBeenCalledWith('a')
      expect(mockAppendChild).toHaveBeenCalled()
      expect(mockClick).toHaveBeenCalled()
      expect(mockRemoveChild).toHaveBeenCalled()
    })
    
    it('should handle values with commas', () => {
      const data = [{ name: 'Test, with comma', value: 100 }]
      const headers = [{ key: 'name', label: 'Name' }]
      
      // Should not throw
      expect(() => exportCSV(data, headers)).not.toThrow()
    })
  })

  describe('exportJSON', () => {
    it('should export JSON with correct format', () => {
      const data = { test: 'data', number: 123 }
      
      exportJSON(data, 'test.json')
      
      expect(document.createElement).toHaveBeenCalledWith('a')
      expect(mockAppendChild).toHaveBeenCalled()
    })
  })
})
