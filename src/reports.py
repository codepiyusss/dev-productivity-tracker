def generate_report(tasks):
    return {
        'total': len(tasks),
        'completed': sum(t.completed for t in tasks)
    }
