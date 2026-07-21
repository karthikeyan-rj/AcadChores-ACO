'use client';

import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Area, AreaChart, Legend
} from 'recharts';
import { useTheme } from '@/lib/theme';

const DARK_COLORS = ['#E8E9EC', '#5FA66A', '#D76A6A', '#D3A04C', '#6F91B7'];
const LIGHT_COLORS = ['#1A1A1A', '#2E7D32', '#A23B3B', '#9A6A13', '#355C7D'];

const DARK_GRID = '#292E37';
const LIGHT_GRID = '#E5E5E0';

const DARK_TEXT = '#A5ABB5';
const LIGHT_TEXT = '#73736D';

const DARK_BG = '#15181E';
const LIGHT_BG = '#FFFFFF';
const DARK_BORDER = '#292E37';
const LIGHT_BORDER = '#E5E5E0';
const DARK_PRIMARY = '#E8E9EC';
const LIGHT_PRIMARY = '#1A1A1A';
const DARK_LABEL = '#A5ABB5';
const LIGHT_LABEL = '#73736D';

interface ChartsProps {
  dailyData: { date: string; completed: number; failed: number; total: number }[];
  statusData: { name: string; value: number }[];
  hourlyData: { hour: string; executions: number }[];
}

export default function Charts({ dailyData, statusData, hourlyData }: ChartsProps) {
  const { resolved } = useTheme();
  const isDark = resolved === 'dark';

  const COLORS = isDark ? DARK_COLORS : LIGHT_COLORS;
  const grid = isDark ? DARK_GRID : LIGHT_GRID;
  const text = isDark ? DARK_TEXT : LIGHT_TEXT;
  const bg = isDark ? DARK_BG : LIGHT_BG;
  const border = isDark ? DARK_BORDER : LIGHT_BORDER;
  const primary = isDark ? DARK_PRIMARY : LIGHT_PRIMARY;
  const label = isDark ? DARK_LABEL : LIGHT_LABEL;

  const tooltipStyle = { background: bg, border: `1px solid ${border}`, borderRadius: '10px', fontSize: '11px', color: primary };

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 rounded-[14px] border border-theme bg-surface p-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-theme-tertiary mb-4">Daily Executions</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" stroke={grid} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: text }} />
              <YAxis tick={{ fontSize: 10, fill: text }} />
              <Tooltip
                contentStyle={tooltipStyle}
                labelStyle={{ color: label }}
                cursor={{ fill: isDark ? '#1A1E25' : '#F4F4F0' }}
              />
              <Bar dataKey="completed" fill={COLORS[1]} radius={[3, 3, 0, 0]} name="Completed" />
              <Bar dataKey="failed" fill={COLORS[2]} radius={[3, 3, 0, 0]} name="Failed" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-[14px] border border-theme bg-surface p-5">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-theme-tertiary mb-4">Status Distribution</h3>
          {statusData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={statusData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} innerRadius={45}>
                  {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip
                  contentStyle={tooltipStyle}
                />
                <Legend
                  wrapperStyle={{ fontSize: '10px' }}
                  formatter={(value: string) => <span style={{ color: label }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-[250px] text-theme-tertiary text-xs">No data</div>
          )}
        </div>
      </div>

      <div className="rounded-[14px] border border-theme bg-surface p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-theme-tertiary mb-4">Hourly Activity</h3>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={hourlyData}>
            <defs>
              <linearGradient id="colorExec" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={primary} stopOpacity={0.3} />
                <stop offset="95%" stopColor={primary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={grid} />
            <XAxis dataKey="hour" tick={{ fontSize: 9, fill: text }} />
            <YAxis tick={{ fontSize: 10, fill: text }} />
            <Tooltip
              contentStyle={tooltipStyle}
              cursor={{ stroke: grid }}
            />
            <Area type="monotone" dataKey="executions" stroke={primary} fillOpacity={1} fill="url(#colorExec)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </>
  );
}
