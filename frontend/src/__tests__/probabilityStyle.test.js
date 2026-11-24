import { expect, it } from 'vitest'
import { probabilityState } from '../utils/probabilityStyle'

it.each([[null,'offline'],[0,'healthy'],[.4999,'healthy'],[.5,'warning'],[.6999,'warning'],[.7,'fault'],[1,'fault']])('概率 %s 对应 %s', (value,state) => {
  expect(probabilityState(value)).toBe(state)
})
