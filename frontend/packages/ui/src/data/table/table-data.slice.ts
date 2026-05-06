/*
This is planned to be deprecated in favor of unified Redux and
Apollo Client store
*/

import {
  createAsyncThunk,
  createSlice,
  type PayloadAction,
} from '@reduxjs/toolkit'

import TableDataServices from './table-data.services'
import { type TableData, type TableDataOptions, type TableInfo } from './table-data.types'
import { type Maybe } from '../../types'
import { isEmpty } from '../../utils/helpers'

interface TableDataState extends TableInfo {
  lastUpdate: Record<string, Maybe<number>>
}

const initialState: TableDataState = {
  data: {},
  metadata: { variables: {}, runs: [], timestamp: 0, tags: {} },
  lastUpdate: {},
}

type TableOptions = Omit<TableDataOptions, 'deferred'>

export const getTable = createAsyncThunk(
  'tableData/get',
  async ({ proposal, page, pageSize, lightweight = false }: TableOptions) => {
    const result = await TableDataServices.getTable({
      proposal,
      page,
      pageSize,
      lightweight,
    })

    return result
  }
)

export const fetchTableMetadata = createAsyncThunk(
  'tableData/fetchMetadata',
  async ({ proposal }: { proposal: string }) => {
    return await TableDataServices.getTableMetadata({ proposal })
  },
  {
    condition: (_, { getState }) => {
      const { tableData } = getState() as { tableData: TableDataState }
      return tableData.metadata.runs.length === 0
    },
  }
)

export const getTableViaPykernApi = createAsyncThunk(
  'tableData/getViaPykernApi',
  async ({ proposal, page = 1, pageSize = 10 }: TableOptions) => {
    return await TableDataServices.getTableDataViaPykernApi({ proposal, page, pageSize })
  },
  {
    condition: ({ page = 1, pageSize = 10 }, { getState }) => {
      const { tableData } = getState() as { tableData: TableDataState }
      const runs = tableData.metadata.runs
      if (runs.length === 0) return false
      const offset = (page - 1) * pageSize
      if (offset >= runs.length) return false
      return !runs.slice(offset, offset + pageSize).every((run) => tableData.data[run] != null)
    },
  }
)

export const getTableData = createAsyncThunk(
  'tableData/getData',
  async ({
    proposal,
    variables,
    page = 1,
    pageSize = 10000,
    deferred = false,
  }: TableDataOptions & { variables: string[] }) => {
    return await TableDataServices.getTableData({
      proposal,
      variables: ['run', ...variables],
      page,
      pageSize,
      deferred,
    })
  }
)

interface UpdateInfo extends TableInfo {
  notify?: boolean
}

const slice = createSlice({
  name: 'tableData',
  initialState,
  reducers: {
    reset: () => initialState,
    update: (state, action: PayloadAction<UpdateInfo>) => {
      const { data, metadata } = action.payload

      // Update data
      if (!isEmpty(data)) {
        const timestamp = performance.now()
        const updatedData = { ...state.data }
        const updatedTimestamp = { ...state.lastUpdate }

        Object.entries(data).forEach(([run, variables]) => {
          updatedData[run] = { ...(updatedData[run] || { run }), ...variables }
          updatedTimestamp[run] = timestamp
        })

        state.data = updatedData
        state.lastUpdate = updatedTimestamp
      }

      // Update metadata
      state.metadata = metadata
    },
  },
  extraReducers: (builder) => {
    builder.addCase(
      getTable.fulfilled,
      (state, action: PayloadAction<TableInfo>) => {
        // TODO: Add pending and rejected
        const { data, metadata } = action.payload
        if (!isEmpty(data)) {
          state.data = { ...state.data, ...data }
          state.metadata = metadata
        }
      }
    )
    builder.addCase(fetchTableMetadata.fulfilled, (state, action) => {
      if (action.payload) {
        state.metadata = action.payload
      }
    })
    builder.addCase(getTableViaPykernApi.fulfilled, (state, action) => {
      const data = action.payload as TableData | undefined
      if (data && !isEmpty(data)) {
        state.data = { ...state.data, ...data }
      }
    })
    builder.addCase(getTableData.fulfilled, (state, action) => {
      // TODO: Add pending and rejected
      const data = action.payload
      const updatedData = { ...state.data }

      Object.entries(data).forEach(([run, variables]) => {
        updatedData[run] = { ...(updatedData[run] || { run }), ...variables }
      })

      state.data = updatedData
    })
  },
})

export default slice.reducer
export const { update: updateTable, reset: resetTable } = slice.actions
