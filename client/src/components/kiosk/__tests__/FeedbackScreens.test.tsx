import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { SuccessScreen, ErrorScreen, ProgressScreen } from '../FeedbackScreens';

describe('SuccessScreen', () => {
  it('calls onContinue after autoReturnMs', () => {
    vi.useFakeTimers();
    const onContinue = vi.fn();
    render(<SuccessScreen message="test" onContinue={onContinue} autoReturnMs={1000} />);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(onContinue).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('renders message', () => {
    render(<SuccessScreen message="Книга выдана" onContinue={() => {}} />);
    expect(screen.getByText('Книга выдана')).toBeInTheDocument();
  });

  it('does not call onContinue before autoReturnMs elapses', () => {
    vi.useFakeTimers();
    const onContinue = vi.fn();
    render(<SuccessScreen message="test" onContinue={onContinue} autoReturnMs={5000} />);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(onContinue).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});

describe('ErrorScreen', () => {
  it('calls onBack after autoReturnMs', () => {
    vi.useFakeTimers();
    const onBack = vi.fn();
    render(<ErrorScreen message="test" onBack={onBack} autoReturnMs={2000} />);
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onBack).toHaveBeenCalled();
    vi.useRealTimers();
  });

  it('renders error message', () => {
    render(<ErrorScreen message="Ошибка авторизации" onBack={() => {}} />);
    expect(screen.getByText('Ошибка авторизации')).toBeInTheDocument();
  });
});

describe('ProgressScreen', () => {
  it('renders progress bar with aria attributes', () => {
    render(<ProgressScreen message="Выдача..." value={42} />);
    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toBeInTheDocument();
    expect(progressbar).toHaveAttribute('aria-valuenow', '42');
    expect(progressbar).toHaveAttribute('aria-valuemin', '0');
    expect(progressbar).toHaveAttribute('aria-valuemax', '100');
  });

  it('renders live region with message', () => {
    render(<ProgressScreen message="Процесс идёт" value={10} />);
    expect(screen.getByText('Процесс идёт')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
