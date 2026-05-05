import { type PayloadAction } from '@reduxjs/toolkit'

import { getTable, getTableData, getTableViaPykernApi } from './table-data.slice'
import { type TableInfo } from './table-data.types'

import { USE_PYKERN_TABLE } from '../../constants'
import { type AppDispatch } from '../../redux/store'
import { isEmpty } from '../../utils/helpers'

export const getDeferredTable =
  ({
    proposal,
    page = 1,
    pageSize = 5,
  }: {
    proposal: string
    page: number
    pageSize: number
  }) =>
  async (dispatch: AppDispatch) => {
    if (USE_PYKERN_TABLE) {
      await dispatch(getTableViaPykernApi({ proposal, page, pageSize }))
      return
    }

    const action = (await dispatch(
      getTable({ proposal, page, pageSize, lightweight: true })
    )) as PayloadAction<TableInfo>

    const { data } = action.payload
    if (isEmpty(data)) {
      return
    }

    const heavyVariables = [
      ...new Set(
        Object.values(data).flatMap((run) =>
          Object.entries(run)
            .filter(([_, variables]) => variables?.value === null)
            .map(([variable]) => variable)
        )
      ),
    ]

    dispatch(
      getTableData({
        proposal,
        variables: heavyVariables,
        page,
        pageSize,
        deferred: true,
      })
    )
  }
